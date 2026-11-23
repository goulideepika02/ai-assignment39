
from flask import Flask, render_template, request
import os
import zipfile
import xml.etree.ElementTree as ET
import html
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = "document_qa_secret_key"
knowledge_base = []

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():

    if "document" not in request.files:
        return "No document selected"

    file = request.files["document"]

    if file.filename == "":
        return "No document selected"

    filename = file.filename.lower()

    if not filename.endswith((".pdf", ".docx", ".txt")):
        return "Unsupported file format"

    safe_filename = secure_filename(file.filename)

    if not safe_filename:
        return "Invalid filename"

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        safe_filename
    )

    file.save(filepath)

    extracted_text = ""
    global knowledge_base
    # PDF Processing
    if filename.endswith(".pdf"):

        return "PDF processing is temporarily unavailable. Please upload DOCX or TXT."

    # DOCX Processing
    elif filename.endswith(".docx"):

        with zipfile.ZipFile(filepath, "r") as docx_file:

            xml_content = docx_file.read("word/document.xml")

            root = ET.fromstring(xml_content)

            namespaces = {
                "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            }

            paragraphs = root.findall(".//w:p", namespaces)

            for paragraph in paragraphs:

                for text in paragraph.findall(".//w:t", namespaces):
                    extracted_text += text.text or ""

                extracted_text += "\n"

    # TXT Processing
    elif filename.endswith(".txt"):

        with open(filepath, "r", encoding="utf-8") as f:
            extracted_text = f.read()
    # Create Knowledge Base
    knowledge_base = [
        sentence.strip()
        for sentence in extracted_text.replace("!", ".").replace("?", ".").split(".")
        if sentence.strip()
    ]
    return f"""
    <h1>Document Uploaded Successfully!</h1>

    <h2>Extracted Information</h2>

    <pre>{html.escape(extracted_text)}</pre>

    <br>

    <a href="/">Go Back Home</a>
    """


@app.route("/ask", methods=["POST"])
def ask():

    question = request.form.get("question", "").strip()

    if not question:
        return "Please enter a question."

    if not knowledge_base:
        return "Please upload a document first."

    question_words = set(
        word.strip(".,?!:;()[]{}\"'").lower()
        for word in question.split()
    )

    best_sentence = ""
    best_score = 0

    for sentence in knowledge_base:

        sentence_words = set(
            word.strip(".,?!:;()[]{}\"'").lower()
            for word in sentence.split()
        )

        score = len(question_words.intersection(sentence_words))

        if score > best_score:
            best_score = score
            best_sentence = sentence

    if best_score > 0:

        return f"""
        <h1>Answer Found!</h1>
        <h3>Your Question:</h3>
        <p>{html.escape(question)}</p>
        <h3>Answer:</h3>
        <p>{html.escape(best_sentence)}</p>
        <a href="/">Go Back Home</a>
        """

    return """
    <h1>Answer Not Found</h1>
    <p>The uploaded document does not contain matching information.</p>
    <a href="/">Go Back Home</a>
    """

@app.route("/evaluate", methods=["POST"])
def evaluate():

    if not knowledge_base:
        return "Please upload a document first."

    test_questions = [
        "What information is available in the document?",
        "What is the main topic of the document?"
    ]

    results = []

    for question in test_questions:

        question_words = set(question.lower().split())

        best_sentence = ""
        best_score = 0

        for sentence in knowledge_base:

            sentence_words = set(sentence.lower().split())

            score = len(question_words.intersection(sentence_words))

            if score > best_score:
                best_score = score
                best_sentence = sentence

        if best_sentence:
            results.append({
                "question": question,
                "answer": best_sentence,
                "status": "Answer Found"
            })
        else:
            results.append({
                "question": question,
                "answer": "No matching information found",
                "status": "No Answer"
            })

    total = len(results)
    answered = sum(
        1 for result in results
        if result["status"] == "Answer Found"
    )

    accuracy = (answered / total) * 100

    output = "<h1>System Evaluation Results</h1>"

    for result in results:
        output += f"""
        <h3>{html.escape(result['question'])}</h3>
        <p>{html.escape(result['answer'])}</p>
        <b>{result['status']}</b>
        <hr>
        """

    output += f"""
    <h2>Evaluation Summary</h2>
    <p>Total Questions: {total}</p>
    <p>Questions Answered: {answered}</p>
    <p>Answer Retrieval Rate: {accuracy:.2f}%</p>
    <a href="/">Go Back Home</a>
    """

    return output

if __name__ == "__main__":
    app.run(debug=True)
