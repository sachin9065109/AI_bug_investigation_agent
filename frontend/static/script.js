async function analyzeBug() {

    const title = document.getElementById("title").value;
    const body = document.getElementById("body").value;

    const response = await fetch("/analyze", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            title,
            body
        })
    });

    const result = await response.json();

    document.getElementById("result").innerHTML =
        `
        Severity: ${result.severity}
        <br>
        Root Cause: ${result.root_cause}
        `;
}
