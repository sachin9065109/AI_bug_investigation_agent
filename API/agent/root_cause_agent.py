def root_cause(issue, slack, sentry):

    if "database" in sentry.lower():
        return "Database timeout issue"

    return "Unknown"
