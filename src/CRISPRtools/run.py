import os
import bz2
import tempfile
import subprocess



# Function to report progress
def future_progress_indicator(future):
    global lock_tasks, tasks_total, tasks_completed
    # obtain the lock
    with lock_tasks:
        if future.result() == 1:
            # update the counter on
            tasks_completed += 1
        # report progress
        print(f' Completed {tasks_completed} of {tasks_total} ...', end='\r', flush=True)

# Function to unzip and run the tool
def unzip_and_run(command_run, input_file, output_file):
    global errors, lock_errors
    tool = command_run[0]
    with open(input_file, 'rb') as file, tempfile.NamedTemporaryFile("wb", suffix="_" + os.path.basename(input_file)[:-8]+".fna", delete=True) as tmp_file:
        decompressor = bz2.BZ2Decompressor()
        for data in iter(lambda : file.read(100 * 1024), b''):
            tmp_file.write(decompressor.decompress(data))
        match tool:
            case "minced":
                completedProcess = subprocess.run(command_run + [tmp_file.name], stdout=open(output_file, 'wb'), stderr=subprocess.DEVNULL)
            case "pilercr":
                completedProcess = subprocess.run(command_run + ['-in', tmp_file.name, '-out', output_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            case "CRISPRDetect3":
                # completedProcess = subprocess.run(['conda', 'run', '-n', 'CRISPRDetect'] + command_run + ['-f', tmp_file.name, '-o', output_file], stdout = subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                completedProcess = subprocess.run(command_run + ['-f', tmp_file.name, '-o', output_file], stdout = subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try: completedProcess.check_returncode()
    except subprocess.CalledProcessError as e: 
        with lock_errors:
            errors.append(f"Error in {input_file}: {tool} returned {e.returncode}")
        return 0
    else:
        return 1

# Function to run the tool
def run(command_run, input_file, output_file):
    global errors, lock_errors
    tool = command_run[0]
    match tool:
        case "minced":
            completedProcess = subprocess.run(command_run + [input_file], check=True, stdout=open(output_file, 'wb'), stderr=subprocess.DEVNULL)
        case "pilercr":
            completedProcess = subprocess.run(command_run + ['-in', input_file, '-out', output_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        case "CRISPRDetect3":
            # completedProcess = subprocess.run(['conda', 'run', '-n', 'CRISPRDetect'] + command_run + ['-f', input_file, '-o', output_file], stdout = subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            completedProcess = subprocess.run(command_run + ['-f', input_file, '-o', output_file], check=True, stdout = subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try: completedProcess.check_returncode()
    except subprocess.CalledProcessError as e: 
        with lock_errors:
            errors.append(f"Error in {input_file}:  {tool} returned {e.returncode}")
        return 0
    else:
        return 1
