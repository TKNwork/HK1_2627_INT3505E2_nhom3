"""Check the workbook routes and the Auth/UC-09 OpenAPI metadata."""
from pathlib import Path
import importlib
import re
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def contract_rows() -> dict[str, dict[str, str]]:
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
          'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
    with zipfile.ZipFile(ROOT / 'docs/api-contract.xlsx') as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            shared = [''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rels = {x.attrib['Id']: x.attrib['Target'] for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        sheets = ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets', ns)
        sheet = next(x for x in sheets if x.attrib['name'] == 'Endpoints')
        target = rels[sheet.attrib['{' + ns['r'] + '}id']]
        path = target.lstrip('/') if target.startswith('/') else 'xl/' + target
        result = {}
        for row in ET.fromstring(z.read(path)).findall('.//s:sheetData/s:row', ns):
            data = {}
            for c in row.findall('s:c', ns):
                v, inline = c.find('s:v', ns), c.find('s:is', ns)
                value = (shared[int(v.text)] if c.attrib.get('t') == 's' and v is not None
                         else ''.join(inline.itertext()) if inline is not None
                         else v.text if v is not None else '')
                data[re.sub(r'\d+', '', c.attrib['r'])] = value
            if re.fullmatch(r'(API|INT)-\d+', data.get('A', '')):
                result[data['A']] = data
        return result


def contract_endpoints() -> dict[str, tuple[str, str]]:
    return {operation: (row['D'], row['E']) for operation, row in contract_rows().items()}


def main() -> None:
    actual = {}
    operations = {}
    for name in ('core', 'ai', 'scheduling', 'notification'):
        app = importlib.import_module(f'services.{name}.main').create_app(init_database_on_startup=False)
        for path, methods in app.openapi()['paths'].items():
            for method, spec in methods.items():
                op = spec.get('operationId', '')
                if op.startswith(('API-', 'INT-')):
                    assert op not in actual, f'Duplicate operationId: {op}'
                    actual[op] = (method.upper(), path)
                    operations[op] = spec
    rows = contract_rows()
    expected = {operation: (row['D'], row['E']) for operation, row in rows.items()}
    assert len(expected) == 22
    assert actual == expected, f'Contract mismatch: expected={expected}, actual={actual}'
    draft_ops = ('API-09', 'API-10', 'API-11', 'API-12', 'API-13')
    for op in ('API-01', 'API-02', *draft_ops, 'INT-01'):
        row = rows[op]
        expected_statuses = {int(row['J'].split()[0]), *map(int, re.findall(r'\b[45]\d{2}\b', row['K']))}
        if row['F'] in ('JWT', 'Service'):
            expected_statuses.add(401)
        missing = expected_statuses - {int(status) for status in operations[op]['responses']}
        assert not missing, f'{op}: missing HTTP responses {sorted(missing)}'
    for op, header in (('API-13', 'Idempotency-Key'), ('INT-01', 'X-Internal-Api-Key')):
        assert any(p['in'] == 'header' and p['name'] == header and p.get('required')
                   for p in operations[op]['parameters']), f'{op}: missing required header {header}'
    for op in draft_ops:
        assert {'HTTPBearer': []} in operations[op]['security'], f'{op}: missing Bearer JWT'
    print('PASS: 22 workbook routes and Auth/UC-09 response and header metadata match.')


if __name__ == '__main__':
    main()
