
## Importing necessary libraries
from langchain_community.document_loaders import  DirectoryLoader,UnstructuredMarkdownLoader,TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import os
from dotenv import load_dotenv
import re
load_dotenv()

## Loading the documents from Code Folder
codes_folder_path = "Codes/"

loader_obj = DirectoryLoader(
    codes_folder_path,
    glob = "**/*.md",# recursively find markdown files
    loader_cls=TextLoader,
    loader_kwargs={"encoding": "utf-8"}
)


docs = loader_obj.load()

# print("Loaded "+ str(len(docs)) + " documents")
# if docs:
#     print(docs[0].metadata)
#     print(docs[0].page_content)

## Splitting documents into chunks
# text_splitter_obj = RecursiveCharacterTextSplitter.from_language(
#     language = "r",
#     chunk_size = 1000,
#     chunk_overlap = 150
# )

# chunks = text_splitter_obj.split_documents(docs)
logical_chunks = []
for doc in docs:
    chunks = [
    chunk.strip()
    for chunk in re.findall(
        r'<!--chunk starts -->(.*?)<!--chunk ends -->',
        doc.page_content,
        flags=re.DOTALL
    )
    if chunk.strip()
]
    
    for chunk in chunks:
        chunk_final = Document(
                        page_content = chunk,
                        metadata = {**doc.metadata}
                            )

        logical_chunks.append(chunk_final)



# print("Original documents:", len(docs))
# print("Logical chunks:", len(logical_chunks))

# # Inspect chunks
# for chunk in logical_chunks[:3]:
#     print("=" * 80)
#     print(chunk.page_content)
#     print(chunk.metadata)

## Creating Embedding of each chunk
os.environ["GOOGLE_API_KEY"] = os.getenv("API_KEY")
embeddings_obj = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001"
)

## Store embedding in Chroma vector store
vectorstore = Chroma.from_documents(
    documents=logical_chunks,
    embedding=embeddings_obj,
    persist_directory="./chroma_db"
)

## Only get the single most similar document from the dataset
retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

## Testing retrieval for a query
#query = "Can you please give me code for random regression using flat prior "

# results = retriever.invoke(query)

# for i,doc in enumerate(results):
#     print("=" * 80)
#     print(f"RESULT {i + 1}")
#     print(doc.page_content)
#     print(doc.metadata)