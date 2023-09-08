import json
import sys

from json2html import json2html


if __name__ == '__main__':
    file = sys.argv[1]
    html = None
    with open(file, encoding="utf8") as json_file:
        data = json.load(json_file)
        html = json2html.convert(json=data)

    with open (f"{file}.html",mode='w', encoding="utf8") as html_file:
        html_file.write(html)

