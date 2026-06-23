import streamlit as st
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda,RunnablePassthrough,RunnableParallel

load_dotenv()
os.makedirs("uploads", exist_ok=True)


ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


password = st.sidebar.text_input(
    "Admin Password",
    type="password"
)
with st.sidebar:
    st.write("Enter Password to Access the Admin.")

if password == ADMIN_PASSWORD:


    with st.sidebar:

        st.title("Admin Panel")

        uploads = st.file_uploader(
            "Upload PDFs",
            type="pdf",
            accept_multiple_files=True
        )

        if uploads:
            for file in uploads:
                with open(f"uploads/{file.name}","wb") as f:
                    f.write(file.getbuffer())

        files = os.listdir("uploads")

        st.subheader("Uploaded Files")

        for file in files:
            st.write("-", file)

        if files:

            delete_file = st.selectbox("Delete PDF",files)

            if st.button("Delete"):
                os.remove(f"uploads/{delete_file}")
                st.rerun()

        

files = os.listdir("uploads")

col1, col2 = st.columns([2,1])

with col1:
    st.title("🤖 Medical AI Assistant")


    st.markdown("""


--**Smart Document Search**
Find information instantly from your uploaded PDFs.

--**AI-Powered Retrieval**
Get accurate, context-aware answers using RAG technology.

--**Fast Responses**
Powered by Gemini AI and FAISS Vector Search.

--**Secure & Private**
Your documents stay protected and confidential.

--**Multi-PDF Support**
Search across multiple documents at once.


    """)


if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.write(message["content"])


all_docs = []

for file in files:
    all_docs.extend(PyPDFLoader(f"uploads/{file}").load())





textsplitter=RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150
)

chunks=textsplitter.split_documents(all_docs)


if len(chunks) == 0:
    st.warning("Please upload at least one PDF")
    st.stop()




embedding=HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

if os.path.exists("faiss_index"):

    vector_store = FAISS.load_local(
        "faiss_index",
        embedding,
        allow_dangerous_deserialization=True
    )

else:

    vector_store = FAISS.from_documents(
        chunks,
        embedding
    )

    vector_store.save_local("faiss_index")


retriever =vector_store.as_retriever(search_type="similarity",search_kwargs={"k":4})

input=st.chat_input("Enter Your message:")


llm=ChatGoogleGenerativeAI(
    model="gemini-2.5-flash"
)


prompt=PromptTemplate(
template=""" 
You are a helpful AI assistant.

Answer the user's question only from the provided context.

If the answer is not present in the context, say:
"I could not find the answer in the uploaded documents."


If the user asks for treatment, diagnosis, medication,
or medical advice, do not provide treatment recommendations.
Say:
"I cannot provide a diagnosis or recommend a specific treatment.
Please consult a qualified healthcare professional or visit the nearest doctor."

Context:
{context}

Question:
{question}

Answer:
""",
    input_variables=["context", "question"]

)


parser=StrOutputParser()

def format_docs(retrieved_docs):
    context="\n\n".join(docs.page_content for docs in retrieved_docs)
    return context

runnable=RunnableParallel({
    "context":retriever|RunnableLambda(format_docs),
    "question":RunnablePassthrough()
})


final_chain = runnable | prompt | llm | parser

if input:

    st.session_state.messages.append({
        "role":"user",
        "content":input
    })

    answer = final_chain.invoke(input)

    st.session_state.messages.append({
        "role":"assistant",
        "content":answer
    })

    with st.chat_message("user"):
        st.write(input) 

    with st.chat_message("assistant"):
        st.write(answer)