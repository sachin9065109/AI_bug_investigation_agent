from bug_prediction.inference import predict_bug

def analyze_bug(title, body):
    severity = predict_bug(title, body)

    return {
        "severity": severity
    }
