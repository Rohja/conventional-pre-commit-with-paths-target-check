import argparse
import sys

from conventional_pre_commit import format
import subprocess

RESULT_SUCCESS = 0
RESULT_FAIL = 1


class Colors:
    LBLUE = "\033[00;34m"
    LRED = "\033[01;31m"
    RESTORE = "\033[0m"
    YELLOW = "\033[00;33m"


def main(argv=[]):
    parser = argparse.ArgumentParser(
        prog="conventional-pre-commit", description="Check a git commit message for Conventional Commits formatting."
    )
    parser.add_argument("types", type=str, nargs="*", default=format.DEFAULT_TYPES, help="Optional list of types to support")
    parser.add_argument(
        "--extra-scopes", nargs="+", default=[], help="Extra scopes to allow in commit messages that are not pants target"
    )
    parser.add_argument("input", type=str, help="A file containing a git commit message")
    parser.add_argument(
        "--force-scope", action="store_false", default=True, dest="optional_scope", help="Force commit to have scope defined."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Force commit to strictly follow Conventional Commits formatting. Disallows fixup! style commits.",
    )

    if len(argv) < 1:
        argv = sys.argv[1:]

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return RESULT_FAIL

    try:
        with open(args.input, encoding="utf-8") as f:
            message = f.read()
    except UnicodeDecodeError:
        print(
            f"""
{Colors.LRED}[Bad Commit message encoding] {Colors.RESTORE}

{Colors.YELLOW}conventional-pre-commit couldn't decode your commit message.{Colors.RESTORE}
{Colors.YELLOW}UTF-8{Colors.RESTORE} encoding is assumed, please configure git to write commit messages in UTF-8.
See {Colors.LBLUE}https://git-scm.com/docs/git-commit/#_discussion{Colors.RESTORE} for more.
        """
        )
        return RESULT_FAIL

    if not args.strict:
        if format.has_autosquash_prefix(message):
            return RESULT_SUCCESS

    is_valid, scope = format.is_conventional(message, args.types, args.optional_scope)
    if is_valid:
        # Check that scope is valid by running `pants list <scope>`
        if scope:
            is_valid_scope = False
            if scope in args.extra_scopes:
                is_valid_scope = True
            else:
                # Check if the scope is a valid pants target
                cmd = ["pants", "list", scope]
                try:
                    result = subprocess.run(cmd)
                except FileNotFoundError:
                    print(
                        f"""
        {Colors.LRED}[Error] >>{Colors.RESTORE} Pants binary was not found, are you sure it's installed and in PATH?"""
                    )
                    return RESULT_FAIL
                # Get the exit code
                if result.returncode == 0:
                    is_valid_scope = True

            if not is_valid_scope:
                print(
                    f"""
        {Colors.YELLOW}[WARNING] >>{Colors.LRED} The scope `{scope}` doesn't seem to be a valid `pants list` scope (return: {result.returncode}).{Colors.RESTORE}
        NOTE: It's not in the allowed extra scopes neither, those are: {Colors.LBLUE}{Colors.RESTORE}
"""
                )
                return RESULT_FAIL
        return RESULT_SUCCESS
    else:
        print(
            f"""
        {Colors.LRED}[Bad Commit message] >>{Colors.RESTORE} {message}
        {Colors.YELLOW}Your commit message does not follow Conventional Commits formatting
        {Colors.LBLUE}https://www.conventionalcommits.org/{Colors.YELLOW}

        Conventional Commits start with one of the below types, followed by a colon,
        followed by the commit subject and an optional body seperated by a blank line:{Colors.RESTORE}

            {" ".join(format.conventional_types(args.types))}

        {Colors.YELLOW}Example commit message adding a feature:{Colors.RESTORE}

            feat: implement new API

        {Colors.YELLOW}Example commit message fixing an issue:{Colors.RESTORE}

            fix: remove infinite loop

        {Colors.YELLOW}Example commit with scope in parentheses after the type for more context:{Colors.RESTORE}

            fix(account): remove infinite loop

        {Colors.YELLOW}Example commit with a body:{Colors.RESTORE}

            fix: remove infinite loop

            Additional information on the issue caused by the infinite loop
            """
        )
        return RESULT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
