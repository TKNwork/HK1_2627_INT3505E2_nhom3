import re
import unicodedata
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from ..schemas.extractions import ExtractionData, ExtractionFields, ExtractionRequest, Warning


def fold(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
                   if unicodedata.category(c) != 'Mn')


def parse_date(text: str, reference: datetime):
    if 'ngay kia' in text:
        return reference.date() + timedelta(days=2)
    if 'ngay mai' in text or re.search(r'\bmai\b', text):
        return reference.date() + timedelta(days=1)
    if 'hom nay' in text:
        return reference.date()
    match = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
    if match:
        return datetime(*map(int, match.groups())).date()
    match = re.search(r'\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b', text)
    if match:
        day, month, year = match.groups()
        return datetime(int(year or reference.year), int(month), int(day)).date()
    match = re.search(r'\b(thu\s*([2-7])|chu nhat)\b', text)
    if match:
        weekday = int(match[2]) - 2 if match[2] else 6
        delta = (weekday - reference.weekday()) % 7
        if 'tuan sau' in text:
            delta = 7 - reference.weekday() + weekday
        return reference.date() + timedelta(days=delta)
    return None


def parse_clock(text: str):
    match = re.search(r'\b(\d{1,2})\s*(?::|h(?=\d|\b)|gio\b)\s*(\d{1,2})?\s*(?:phut)?\s*(ruoi)?\s*(sang|chieu|toi|trua)?', text)
    if not match:
        return None
    hour, minute, half, period = match.groups()
    hour, minute = int(hour), 30 if half else int(minute or 0)
    if period in ('chieu', 'toi') and hour < 12:
        hour += 12
    if period == 'sang' and hour == 12:
        hour = 0
    return time(hour, minute)


def summarize(fields: ExtractionFields, warnings: list[Warning]) -> ExtractionData:
    missing = [alias for name, alias in [('title', 'title'), ('date', 'date'),
               ('start_at', 'startAt'), ('duration_minutes', 'durationMinutes')]
               if getattr(fields, name) is None]
    required = [name for name in missing if name in ('title', 'durationMinutes')]
    if fields.date is None and fields.start_at is None and fields.deadline_at is None:
        required.append('date')
    return ExtractionData(fields=fields, missing_fields=missing,
                          required_input_fields=required, warnings=warnings)


def normalize(fields: ExtractionFields, body: ExtractionRequest,
              warnings: list[Warning] | None = None) -> ExtractionData:
    warnings = list(warnings or [])
    fields.timezone = body.timezone
    zone = ZoneInfo(body.timezone)
    if fields.title is not None:
        fields.title = fields.title.strip() or None
    if fields.start_at:
        fields.start_at = fields.start_at.astimezone(zone)
        local_date = fields.start_at.date()
        if fields.date and fields.date != local_date:
            raise ValueError('date và startAt không khớp')
        fields.date = local_date
        if fields.start_at < body.now:
            warnings.append(Warning(code='PAST_START', message='Giờ bắt đầu đã qua.'))
    if fields.deadline_at and fields.deadline_at < body.now:
        warnings.append(Warning(code='PAST_DEADLINE', message='Hạn hoàn thành đã qua.'))
    if fields.start_at and fields.duration_minutes and fields.deadline_at:
        if fields.start_at + timedelta(minutes=fields.duration_minutes) > fields.deadline_at:
            warnings.append(Warning(code='DEADLINE_EXCEEDED', message='Thời gian kết thúc vượt hạn hoàn thành.'))
    return summarize(fields, warnings)


def extract_rules(body: ExtractionRequest) -> ExtractionData:
    original = unicodedata.normalize('NFC', body.source_text).strip()
    text = fold(original)
    reference = body.now.astimezone(ZoneInfo(body.timezone))
    warnings = []
    fields = ExtractionFields(timezone=body.timezone)
    deadline_match = re.search(r'\b(?:xong truoc|hoan thanh truoc|han chot|deadline|truoc)\b', text)
    main = text[:deadline_match.start()] if deadline_match else text
    try:
        fields.date = parse_date(main, reference)
        duration = re.search(r'\b(?:trong|keo dai|thoi luong)\s*(\d+(?:[.,]\d+)?)\s*(phut|tieng|gio)(?:\s*(ruoi|\d+\s*phut))?', main)
        if not duration:
            duration = re.search(r'\b(\d+)\s*(phut|tieng)\b', main)
        clock_text = main
        if duration:
            amount, unit = duration[1], duration[2]
            minutes = float(amount.replace(',', '.')) * (1 if unit == 'phut' else 60)
            suffix = duration[3] if duration.lastindex >= 3 else None
            if suffix:
                minutes += 30 if suffix == 'ruoi' else int(re.search(r'\d+', suffix)[0])
            if minutes.is_integer() and 1 <= minutes <= 1440:
                fields.duration_minutes = int(minutes)
            else:
                warnings.append(Warning(code='INVALID_DURATION', message='Thời lượng phải từ 1 đến 1440 phút.'))
            clock_text = main[:duration.start()] + ' ' * (duration.end() - duration.start()) + main[duration.end():]
        interval = re.search(r'\btu\s+(.+?)\s+den\s+(.+)', clock_text)
        start_clock = parse_clock(interval[1] if interval else clock_text)
        if start_clock and fields.date:
            fields.start_at = datetime.combine(fields.date, start_clock, reference.tzinfo)
        elif start_clock:
            warnings.append(Warning(code='DATE_REQUIRED', message='Có giờ nhưng chưa xác định ngày.'))
        if interval:
            end_clock = parse_clock(interval[2])
            if fields.start_at and end_clock:
                end = datetime.combine(fields.date, end_clock, reference.tzinfo)
                inferred = int((end - fields.start_at).total_seconds() / 60)
                if inferred <= 0:
                    warnings.append(Warning(code='AMBIGUOUS_TIME_RANGE', message='Cần làm rõ khoảng giờ qua ngày.'))
                elif fields.duration_minutes and fields.duration_minutes != inferred:
                    warnings.append(Warning(code='DURATION_CONFLICT', message='Thời lượng không khớp khoảng giờ.'))
                    fields.duration_minutes = None
                else:
                    fields.duration_minutes = inferred
        if deadline_match:
            tail = text[deadline_match.end():]
            deadline_date = parse_date(tail, reference) or fields.date
            deadline_clock = parse_clock(tail)
            if deadline_date and deadline_clock:
                fields.deadline_at = datetime.combine(deadline_date, deadline_clock, reference.tzinfo)
            else:
                warnings.append(Warning(code='AMBIGUOUS_DEADLINE', message='Cần bổ sung ngày và giờ cho deadline.'))
    except ValueError:
        warnings.append(Warning(code='INVALID_DATE_TIME', message='Ngày hoặc giờ không hợp lệ; cần kiểm tra lại.'))
    # Các mẫu có cùng độ dài sau fold nên giữ được dấu tiếng Việt khi cắt tiêu đề.
    title = original[:deadline_match.start()] if deadline_match else original
    for pattern in [r'\b(?:ngay mai|ngay kia|hom nay|mai)\b', r'\b\d{4}-\d{2}-\d{2}\b',
                    r'\b\d{1,2}/\d{1,2}(?:/\d{4})?\b', r'\b(?:thu\s*[2-7]|chu nhat)(?:\s+tuan sau)?\b',
                    r'\b(?:trong|keo dai|thoi luong)\s*\d+(?:[.,]\d+)?\s*(?:phut|tieng|gio)(?:\s*(?:ruoi|\d+\s*phut))?',
                    r'\b\d+\s*(?:phut|tieng)\b',
                    r'\b(?:tu\s+|luc\s+)?\d{1,2}\s*(?::|h(?=\d|\b)|gio\b)\s*\d{0,2}\s*(?:phut)?\s*(?:ruoi)?\s*(?:sang|chieu|toi|trua)?',
                    r'\bden\s*$', r'^\s*(?:hay|giup toi|nhac toi|toi can)\s+']:
        matches = list(re.finditer(pattern, fold(title)))
        for match in reversed(matches):
            title = title[:match.start()] + ' ' * len(match[0]) + title[match.end():]
    fields.title = re.sub(r'\s+', ' ', title).strip(' ,.;:-') or None
    if fields.title and len(fields.title) > 200:
        fields.title = None
        warnings.append(Warning(code='TITLE_TOO_LONG', message='Cần rút gọn tiêu đề còn tối đa 200 ký tự.'))
    if not fields.date and not fields.start_at:
        warnings.append(Warning(code='DATE_REQUIRED', message='Chưa xác định ngày thực hiện.'))
    return normalize(fields, body, warnings)
