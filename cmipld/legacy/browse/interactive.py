import os
import shlex


import json
import tempfile
import io
import urllib.parse
import atexit
import subprocess


def write_dict_to_tempfile(data):
    # Ensure the input is a dictionary
    # if not isinstance(data, dict):
    #     raise ValueError("Input data must be a dictionary")

    # Create a temporary file with a specific suffix for easier access
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix=".json")
    try:
        # Write the dictionary as JSON to the file
        json.dump(data, temp_file, indent=4)
        temp_file_name = temp_file.name

        # URL encode the file path to make it safe
        # temp_file_url = urllib.parse.quote(temp_file_name)

        print(
            f"Dictionary written to temporary file at URL-safe path: {temp_file_name}")

        # Register cleanup to delete the temp file on exit

        return temp_file_name
    finally:
        temp_file.close()


def cleanup_temp_file(file_path):
    """Delete the temporary file upon script exit."""
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Temporary file {file_path} has been deleted.")


def open_command_line_program(temp):
    # Prompt user for the command to run
    # command = input("Enter the command-line program you want to open (e.g., 'bash', 'python', 'ping google.com'): ")

    # Split the command into executable and arguments
    args = shlex.split(f"jless {temp}")
    program = args[0]

    try:
        # Replace the current process with the command-line program
        os.execvp(program, args)
    except FileNotFoundError:
        print(f"Error: '{program}' not found.")
    except Exception as e:
        print(f"An error occurred while trying to open '{args}': {e}")


def open_jless_with_memory(temp):
    # Create an in-memory file-like object using StringIO
    mem_file = io.StringIO(json.dumps(temp))

    # Use bash to execute the command (bash will read the input from memory)
    # Use subprocess to pipe the in-memory file content to jless
    try:
        # Run `jless` and send the in-memory content via stdin
        # Note: jless will take over the terminal in the foreground
        subprocess.run(['jless', '--mode', 'line'],
                       input=mem_file.getvalue().encode())
    except FileNotFoundError:
        print("Error: jless not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def interact(data):
    # temp = write_dict_to_tempfile(data)
    #     print(f"temporary file created at {temp}")
    # open_command_line_program(temp)
    open_jless_with_memory(data)
    # atexit.register(cleanup_temp_file, temp)

# if __name__ == "__main__":

    # data = {"key": "value", "number": {"a":123,"b":456}}
    # temp = write_dict_to_tempfile(data)
    # print(temp)
    # open_command_line_program(temp)
    # atexit.register(cleanup_temp_file, temp)
