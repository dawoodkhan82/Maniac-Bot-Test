import os
from datetime import datetime


FLAGS_TEXT_PATH = 'flags.txt'
TEST_FILE_PATH = 'test_file.py'


def get_content():
    with open(TEST_FILE_PATH) as f:
        content = f.readlines()
    return [x.strip() for x in content]


def get_fn_lines():
    file_content = get_content()

    functions = [f for f in file_content if f[:3] == "def"]

    lines = {}
    for index, function in enumerate(functions):
        fn_name = function.split('(')[0].split(" ")[1]
        fn_line = file_content.index(function)
        if index == len(functions) - 1:
            if '"""' in file_content[fn_line:]:
                doc_init = fn_line + file_content[fn_line:].index('"""')
                doc_end = doc_init + 1 + file_content[doc_init + 1:].index(
                    '"""')
                code_init = doc_end + 1
                code_end = len(file_content) - 1
            else:
                doc_init = None
                doc_end = None
                code_init = fn_line + 1
                code_end = len(file_content) - 1
        else:
            next_fn_line = file_content.index(functions[index+1])
            if '"""' in file_content[fn_line: next_fn_line]:
                doc_init = fn_line + file_content[fn_line:
                                                   next_fn_line].index('"""')
                doc_end = doc_init + 1 + file_content[doc_init+1:
                                                next_fn_line].index('"""')
                code_init = doc_end + 1
                code_end = next_fn_line - 1
            else:
                doc_init = None
                doc_end = None
                code_init = fn_line + 1
                code_end = next_fn_line - 1

        lines[fn_name] = {
            "fn_line": fn_line,
            "doc_init": doc_init,
            "doc_end": doc_end,
            "code_init": code_init,
            "code_end": code_end
        }
    return lines


def convert_to_datetime(string):
    datetime_object = datetime.strptime(string, '%Y-%m-%d %H:%M:%S')
    return datetime_object


def run_flags():
    lines = get_fn_lines()
    stream = os.popen(f'git blame {TEST_FILE_PATH}')
    output = stream.readlines()
    output = [x.strip() for x in output]

    flags = {}
    for fn in lines.keys():
        doc_output = output[lines[fn]["doc_init"]:lines[fn]["doc_end"]]
        code_output = output[lines[fn]["code_init"]:lines[fn]["code_end"]]

        doc_output_dates = [" ".join(item.split(' ')[2:4]) for item in
                            doc_output]
        code_output_dates = [" ".join(item.split(' ')[2:4]) for item in
                             code_output]
        doc_output_dates = [convert_to_datetime(item) for item in
                            doc_output_dates]
        code_output_dates = [convert_to_datetime(item) for item in
                             code_output_dates]

        latest_doc_date = max(doc_output_dates)
        latest_code_date = max(code_output_dates)

        if latest_code_date > latest_doc_date:
            stale = True
            time_behind = latest_code_date - latest_doc_date
            last_doc_commit = doc_output[doc_output_dates.index(
                latest_doc_date)].split(" ")[0]
            code_user = code_output[code_output_dates.index(
                latest_code_date)].split(" ")[1][1:]
        else:
            stale = False
            time_behind = None
            last_doc_commit = None
            code_user = None

        flags[fn] = {
            "stale": stale,
            "time_behind": time_behind,
            "last_doc_commit": last_doc_commit,
            "code_user": code_user
        }

    return flags


def save_flags():
    flags = run_flags()
    text = []
    for fn in flags.keys():
        if flags[fn]["stale"]:
            time_behind = flags[fn]["time_behind"]
            last_doc_commit = flags[fn]["last_doc_commit"]
            code_user = flags[fn]["code_user"]

            text.append(f"FUNCTION: {fn} | STALE: TRUE | TIME BEHIND: "
                        f"{time_behind} | LAST DOC COMMIT: {last_doc_commit} "
                        f"| CODE UPDATED BY: {code_user}")
        else:
            text.append(f"FUNCTION: {fn} | STALE: FALSE")

    with open(FLAGS_TEXT_PATH, 'w') as f:
        for item in text:
            f.write("%s\n" % item)


save_flags()
