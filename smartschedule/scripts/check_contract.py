"""Compare all 22 OpenAPI operation IDs/paths with the read-only Excel contract."""
from pathlib import Path
import importlib
import re
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def contract_endpoints() -> dict[str, tuple[str, str]]:
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
                result[data['A']] = (data['D'], data['E'])
        return result


def main() -> None:
    actual = {}
    for name in ('core', 'ai', 'scheduling', 'notification'):
        app = importlib.import_module(f'services.{name}.main').create_app(init_database_on_startup=False)
        for path, methods in app.openapi()['paths'].items():
            for method, spec in methods.items():
                op = spec.get('operationId', '')
                if op.startswith(('API-', 'INT-')):
                    assert op not in actual, f'Duplicate operationId: {op}'
                    actual[op] = (method.upper(), path)
    expected = contract_endpoints()
    assert len(expected) == 22
    assert actual == expected, f'Contract mismatch: expected={expected}, actual={actual}'
    print('PASS: all 22 endpoints match method, path and operationId in docs/api-contract.xlsx.')


if __name__ == '__main__':
    main()
