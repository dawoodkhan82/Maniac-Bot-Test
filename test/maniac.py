import os
from datetime import datetime
import ast

FLAGS_TEXT_PATH = 'flags.txt'
TEST_FILE_PATH = 'test_file.py'

NODE_TYPES = {
    ast.ClassDef: 'Class',
    ast.FunctionDef: 'Function/Method',
    ast.AsyncFunctionDef: 'AsyncFunction/Method',
}


def get_line_numbers(source):
    tree = ast.parse(source)
    line_numbers = {}

    for node in ast.walk(tree):
        if isinstance(node, tuple(NODE_TYPES)):
            name = getattr(node, 'name', None)
            function_lineno = getattr(node, 'lineno', None)
            doc_lineno_start, doc_lineno_end = None, None
            code_lines = [body.lineno for body in node.body if not
            isinstance(body, ast.Expr)]
            code_lineno_start, code_lineno_end = min(code_lines) - 1, \
                                                 max(code_lines) - 1

            if (node.body and isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, ast.Str)):
                doc_lineno_end = node.body[0].lineno - 1
                doc_lineno_start = doc_lineno_end - len(node.body[
                                                0].value.s.splitlines())
            line_numbers[name] = {
                "type": NODE_TYPES[(type(node))],
                "function_lineno": function_lineno,
                "doc_lineno_start": doc_lineno_start,
                "doc_lineno_end": doc_lineno_end,
                "code_lineno_start": code_lineno_start,
                "code_lineno_end": code_lineno_end
            }
    return line_numbers


def convert_to_datetime(string):
    datetime_object = datetime.strptime(string, '%Y-%m-%d %H:%M:%S')
    return datetime_object


def git_blame(fp):
    stream = os.popen(f'git blame {fp}')
    output = stream.readlines()
    output = [x.strip() for x in output]
    return output


def run_flags(source):
    lines = get_line_numbers(source)
    output = git_blame(TEST_FILE_PATH)

    flags = {}
    for name in lines.keys():
        if lines[name]["doc_lineno_start"]:
            if lines[name]["doc_lineno_start"] == \
                    lines[name]["doc_lineno_end"]:
                doc_output = output[lines[name]["doc_lineno_start"]]
                doc_output_dates = " ".join(doc_output.split(' ')[2:4])
                latest_doc_date = convert_to_datetime(doc_output_dates)
            else:
                doc_output = output[lines[name]["doc_lineno_start"]:lines[name][
                    "doc_lineno_end"]]
                doc_output_dates = [" ".join(item.split(' ')[2:4]) for item in
                                    doc_output]
                doc_output_dates = [convert_to_datetime(item) for item in
                                    doc_output_dates]
                latest_doc_date = max(doc_output_dates)
        else:
            latest_doc_date = None

        if lines[name]["code_lineno_start"] == lines[name]["code_lineno_end"]:
            code_output = output[lines[name]["code_lineno_start"]]
            code_output_dates = " ".join(code_output.split(' ')[2:4])
            latest_code_date = convert_to_datetime(code_output_dates)
        else:
            code_output = output[lines[name]["code_lineno_start"]:lines[name][
                "code_lineno_end"]]
            code_output_dates = [" ".join(item.split(' ')[2:4]) for item in
                                 code_output]
            code_output_dates = [convert_to_datetime(item) for item in
                                 code_output_dates]
            latest_code_date = max(code_output_dates)

        if not latest_doc_date:
            missing = True
            stale = True
            time_behind = None
            last_doc_commit = None
            if lines[name]["code_lineno_start"] == \
                    lines[name]["code_lineno_end"]:
                code_user = code_output.split(" ")[1][1:]
            else:
                code_user = code_output[code_output_dates.index(
                    latest_code_date)].split(" ")[1][1:]
        elif latest_code_date > latest_doc_date:
            stale = True
            missing = False
            time_behind = latest_code_date - latest_doc_date
            if lines[name]["doc_lineno_start"] == \
                    lines[name]["doc_lineno_end"]:
                last_doc_commit = doc_output.split(" ")[0]
            else:
                last_doc_commit = doc_output[doc_output_dates.index(
                    latest_doc_date)].split(" ")[0]
            if lines[name]["code_lineno_start"] == \
                    lines[name]["code_lineno_end"]:
                code_user = code_output.split(" ")[1][1:]
            else:
                code_user = code_output[code_output_dates.index(
                    latest_code_date)].split(" ")[1][1:]
        else:
            stale = False
            missing = False
            time_behind = None
            last_doc_commit = None
            code_user = None

        flags[name] = {
            "is_stale": stale,
            "is_missing": missing,
            "time_behind": time_behind,
            "last_doc_commit": last_doc_commit,
            "code_user": code_user
        }

    return flags


def save_flags():
    with open(TEST_FILE_PATH) as fp:
        source = fp.read()
        flags = run_flags(source)
        stale_docs, missing_docs, passed = [], [], []
        for fn in flags.keys():
            if flags[fn]["is_missing"]:
                missing_docs.append(f"{fn} |"
                                    f" CODE UPDATED BY: {code_user}")
            elif flags[fn]["is_stale"]:
                time_behind = flags[fn]["time_behind"]
                last_doc_commit = flags[fn]["last_doc_commit"]
                code_user = flags[fn]["code_user"]

                stale_docs.append(f"{fn} | TIME BEHIND: "
                            f"{time_behind} | LAST DOC COMMIT: "
                            f"{last_doc_commit} "
                            f"| CODE UPDATED BY: {code_user}")
            else:
                passed.append(f"{fn} ")

    with open(FLAGS_TEXT_PATH, 'w') as f:
        f.write("STALE DOCSTRINGS:\n")
        f.write("-"*len("STALE DOCSTRINGS:") + "\n")
        for item in stale_docs:
            f.write("%s\n" % item)
        f.write("\nMISSING DOCSTRINGS:\n")
        f.write("-" * len("MISSING DOCSTRINGS:") + "\n")
        for item in missing_docs:
            f.write("%s\n" % item)
        f.write("\nUP TO DATE:\n")
        f.write("-" * len("UP TO DATE:") + "\n")
        for item in passed:
            f.write("%s\n" % item)


save_flags()
