import traceback

def log_nonfatal(exception: Exception):
    print("Nonfatal error:")
    print(traceback.format_exc())
