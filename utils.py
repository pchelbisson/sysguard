

def handle_error(report_dict, msg, is_critical):
    """Updates the report dictionary and logs the error."""
    
    if is_critical:
        report_dict["status"] = "ERROR"
        report_dict["data"]["is_critical_failure"] = True
    else:
        report_dict["status"] = "WARNING"
    report_dict["message"] = msg