import re
import unicodedata
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from ..schemas.extractions import ExtractionData, ExtractionFields, ExtractionRequest, Warning


WEEKDAYS = {'2': 0, 'hai': 0, '3': 1, 'ba': 1, '4': 2, 'tu': 2, 'bon': 2,
            '5': 3, 'nam': 3, '6': 4, 'sau': 4, '7': 5, 'bay': 5}
WEEKDAY = r'(?:thu\s*(?:[2-7]|hai|ba|tu|bon|nam|sau|bay)|chu nhat)'
RELATIVE_DATE = r'(?:ngay kia|ngay mai|hom nay|toi nay|sang nay|chieu nay|trua nay|mai)'
NUMERIC_DATE = r'(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{4})?)'
DATE = rf'\b(?:{RELATIVE_DATE}|{NUMERIC_DATE}|{WEEKDAY}(?:\s+tuan sau)?)\b'
CLOCK = re.compile(
    r'\b(?P<hour>\d{1,2})(?:\s*:\s*(?P<colon_minute>\d+)|'
    r'\s*h(?=\d|\b)(?:(?P<compact_minute>\d+)|\s+(?P<h_minute>\d+)\s*phut\b)?|'
    r'\s*gio\b(?:\s+(?P<word_minute>\d+)\s*phut\b)?)'
    r'(?:\s*(?P<half>ruoi)\b)?(?:\s*(?P<period>sang|chieu|toi|trua)\b)?'
)
EXPLICIT_DURATION = re.compile(
    r'\b(?:trong|keo dai|thoi luong)\s*(\d+(?:[.,]\d+)?)\s*(phut|tieng|gio)\b'
    r'(?:\s*(ruoi|\d+\s*phut)\b)?'
)
BARE_DURATION = re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(phut|tieng)\b(?:\s*(ruoi)\b)?')
DEADLINE = re.compile(r'\b(?:xong truoc|hoan thanh truoc|han chot|deadline|truoc)\b\s*:?\s*')
DEADLINE_TIME = re.compile(rf'(?:{DATE}\s*(?:luc\s+)?)?{CLOCK.pattern}(?:\s+{DATE})?')


def fold(text: str) -> str:
    """Bỏ dấu và chuyển chữ thường để so mẫu; tiêu đề vẫn lấy từ câu gốc."""
    folded = []
    for char in text:
        base = ''.join(c for c in unicodedata.normalize('NFD', char.lower().replace('đ', 'd'))
                       if unicodedata.category(c) != 'Mn')
        folded.append(base if len(base) == 1 else char)
    return ''.join(folded)


def temporal_text(original: str) -> str:
    text = fold(original)
    for match in re.finditer(r'\bmai\b', text):
        start = match.start()
        prefix = text[:start].rstrip()
        is_date = re.search(r'\b(?:ngay|sang|chieu|toi|trua)\s*$', prefix)
        if not is_date and (re.search(r'\bvoi$', prefix) or (start and original[start:match.end()] == 'Mai')):
            text = text[:start] + '___' + text[match.end():]
    return text


def parse_date(text: str, reference: datetime):
    """Đọc ngày theo mốc tham chiếu; không nhận ra trả None, ngày sai gây ValueError."""
    if re.search(r'\bngay kia\b', text):
        return reference.date() + timedelta(days=2)
    if re.search(r'\bmai\b', text):
        return reference.date() + timedelta(days=1)
    if re.search(r'\b(?:hom|toi|sang|chieu|trua) nay\b', text):
        return reference.date()
    match = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
    if match:
        return datetime(*map(int, match.groups())).date()
    match = re.search(r'\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b', text)
    if match:
        day, month, year = match.groups()
        return datetime(int(year or reference.year), int(month), int(day)).date()
    match = re.search(rf'\b{WEEKDAY}(?:\s+tuan sau)?\b', text)
    if match:
        parts = match[0].removesuffix(' tuan sau')
        weekday = 6 if parts == 'chu nhat' else WEEKDAYS[parts[3:].strip()]
        delta = (weekday - reference.weekday()) % 7
        if match[0].endswith(' tuan sau'):
            delta = 7 - reference.weekday() + weekday
        return reference.date() + timedelta(days=delta)
    return None


def clock_value(match: re.Match) -> time:
    minutes = [match[name] for name in ('colon_minute', 'compact_minute', 'h_minute', 'word_minute')
               if match[name] is not None]
    if match['half'] and minutes:
        raise ValueError('Phút bị lặp.')
    hour = int(match['hour'])
    minute = 30 if match['half'] else int(minutes[0]) if minutes else 0
    period = match['period']
    if period in ('chieu', 'toi') and hour < 12:
        hour += 12
    if period == 'sang' and hour == 12:
        hour = 0
    return time(hour, minute)


def parse_clock(text: str, period: str | None = None):
    match = CLOCK.search(text)
    if match is None:
        return None
    clock = clock_value(match)
    if not match['period'] and period in ('chieu', 'toi') and clock.hour < 12:
        clock = clock.replace(hour=clock.hour + 12)
    return clock


def local_datetime(day, clock: time, zone: ZoneInfo) -> datetime:
    value = datetime.combine(day, clock, zone)
    if value.utcoffset() != value.replace(fold=1).utcoffset():
        raise ValueError('Giờ địa phương bị lặp hoặc không tồn tại.')
    return value


def mask(text: str, start: int, end: int) -> str:
    return text[:start] + ' ' * (end - start) + text[end:]


def summarize(fields: ExtractionFields, warnings: list[Warning]) -> ExtractionData:
    """Xác định trường còn thiếu và trường người dùng cần bổ sung."""
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
    """Đối chiếu ngày giờ theo timezone và cảnh báo quá hạn; chưa kiểm tra lịch bận."""
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
        if fields.start_at.astimezone(timezone.utc) < body.now.astimezone(timezone.utc):
            warnings.append(Warning(code='PAST_START', message='Giờ bắt đầu đã qua.'))
    if fields.deadline_at:
        fields.deadline_at = fields.deadline_at.astimezone(zone)
        if fields.deadline_at.astimezone(timezone.utc) <= body.now.astimezone(timezone.utc):
            warnings.append(Warning(code='PAST_DEADLINE', message='Hạn hoàn thành đã qua.'))
    if fields.start_at and fields.duration_minutes and fields.deadline_at:
        if fields.start_at.astimezone(timezone.utc) + timedelta(minutes=fields.duration_minutes) > fields.deadline_at.astimezone(timezone.utc):
            warnings.append(Warning(code='DEADLINE_EXCEEDED', message='Thời gian kết thúc vượt hạn hoàn thành.'))
    return summarize(fields, warnings)


def extract_rules(body: ExtractionRequest) -> ExtractionData:
    """Trích xuất một công việc bằng các mẫu ngày, giờ, thời lượng và deadline."""
    original = unicodedata.normalize('NFC', body.source_text).strip()
    text = temporal_text(original)
    reference = body.now.astimezone(ZoneInfo(body.timezone))
    warnings = []
    fields = ExtractionFields(timezone=body.timezone)
    main = text
    title = original
    deadline_at = None
    for marker in DEADLINE.finditer(text):
        candidate = DEADLINE_TIME.match(text, marker.end())
        if candidate is not None:
            try:
                clock_value(candidate)
            except ValueError:
                continue
            # A date/time phrase marks the deadline. Preserve any text following it.
            deadline_at = candidate
            main = mask(text, marker.start(), candidate.end())
            title = mask(original, marker.start(), candidate.end())
            break
    try:
        fields.date = parse_date(main, reference)
        duration = EXPLICIT_DURATION.search(main)
        if not duration:
            clocks = list(CLOCK.finditer(main))
            duration = next((candidate for candidate in BARE_DURATION.finditer(main)
                             if all(candidate.end() <= clock.start() or candidate.start() >= clock.end()
                                    for clock in clocks)), None)
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
            clock_text = mask(main, duration.start(), duration.end())
            title = mask(title, duration.start(), duration.end())
        interval = re.search(r'\btu\s+(.+?)\s+(den)\s+(.+)', clock_text)
        period_match = re.search(rf'\b(sang|chieu|toi|trua)\s+(?:nay|{WEEKDAY})\b', main)
        period = period_match[1] if period_match else None
        start_clock = parse_clock(clock_text, period)
        end_clock = None
        if interval:
            first, last = CLOCK.search(interval[1]), CLOCK.search(interval[3])
            if first and last:
                first_value, last_value = clock_value(first), clock_value(last)
                if not period and int(first['hour']) <= int(last['hour']) < 12:
                    period = first['period'] or last['period']
                start_clock = parse_clock(interval[1], period) if period else first_value
                end_clock = parse_clock(interval[3], period) if period else last_value
                title = mask(title, *interval.span(2))
        if start_clock and fields.date:
            fields.start_at = local_datetime(fields.date, start_clock, reference.tzinfo)
        if fields.start_at and end_clock:
            end = local_datetime(fields.date, end_clock, reference.tzinfo)
            inferred = int((end.astimezone(timezone.utc) -
                            fields.start_at.astimezone(timezone.utc)).total_seconds() / 60)
            if inferred <= 0:
                warnings.append(Warning(code='AMBIGUOUS_TIME_RANGE', message='Cần làm rõ khoảng giờ qua ngày.'))
            elif inferred > 1440:
                fields.duration_minutes = None
                warnings.append(Warning(code='INVALID_DURATION', message='Thời lượng phải từ 1 đến 1440 phút.'))
            elif fields.duration_minutes and fields.duration_minutes != inferred:
                warnings.append(Warning(code='DURATION_CONFLICT', message='Thời lượng không khớp khoảng giờ.'))
                fields.duration_minutes = None
            else:
                fields.duration_minutes = inferred
        if deadline_at is not None:
            deadline_date = parse_date(deadline_at[0], reference) or fields.date
            deadline_clock = clock_value(deadline_at)
            if deadline_date:
                fields.deadline_at = local_datetime(deadline_date, deadline_clock, reference.tzinfo)
            else:
                warnings.append(Warning(code='AMBIGUOUS_DEADLINE', message='Cần bổ sung ngày và giờ cho deadline.'))
    except (ValueError, OverflowError):
        warnings.append(Warning(code='INVALID_DATE_TIME', message='Ngày hoặc giờ không hợp lệ; cần kiểm tra lại.'))
    for pattern in [rf'(?:\b(?:sang|chieu|toi|trua|ngay)\s+)?{DATE}',
                    rf'(?:\b(?:tu|luc)\s+)?{CLOCK.pattern}',
                    r'^\s*(?:hay|giup toi|nhac toi|toi can)\s+']:
        matches = list(re.finditer(pattern, temporal_text(title)))
        for match in reversed(matches):
            title = mask(title, match.start(), match.end())
    fields.title = re.sub(r'\s+', ' ', title).strip(' ,.;:-') or None
    if fields.title and len(fields.title) > 200:
        fields.title = None
        warnings.append(Warning(code='TITLE_TOO_LONG', message='Cần rút gọn tiêu đề còn tối đa 200 ký tự.'))
    if not fields.date and not fields.start_at and not fields.deadline_at:
        warnings.append(Warning(code='DATE_REQUIRED', message='Chưa xác định ngày thực hiện.'))
    return normalize(fields, body, warnings)
