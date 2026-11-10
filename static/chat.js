async function sendMessage(){

    let message = document.getElementById("message").value
    let chatbox = document.getElementById("chatbox")

    chatbox.innerHTML += "<b>You:</b> " + message + "<br>"

    let response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            student_id: "1001",
            message: message
        })
    })

    let data = await response.json()

    let formatted = marked.parse(data.response)

    chatbox.innerHTML += "<div><b>AI:</b>" + formatted + "</div>"

    document.getElementById("message").value = ""
}