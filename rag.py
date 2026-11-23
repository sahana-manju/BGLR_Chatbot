
## Importing necessary libraries
from langchain_community.document_loaders import  DirectoryLoader,UnstructuredMarkdownLoader,TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import os
from dotenv import load_dotenv
import re
from database import SessionLocal, engine, Base, get_db
from sqlalchemy.orm import Session
import models
load_dotenv()

## Load Postgres Database instance

Base.metadata.create_all(bind=engine)
db = SessionLocal()

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

def extract_section(pattern, text):

    match = re.search(
        pattern,
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    return match.group(1).strip() if match else ""

# chunks = text_splitter_obj.split_documents(docs)
logical_chunks = []
try:
    for doc in docs:
        text = doc.page_content

        source = doc.metadata.get("source", "")

        # Extract markdown filename without extension
        document_id = os.path.splitext(os.path.basename(source))[0]
        print(document_id)

        # Extract introduction
        intro = extract_section(
            r'<!--\s*intro starts\s*-->(.*?)<!--\s*intro ends\s*-->',
            text
        )

        # Extract optional skills
        skills = extract_section(
            r'<!--\s*skills starts\s*-->(.*?)<!--\s*skills ends\s*-->',
            text
        )

        chunks = [
        chunk.strip()
        for chunk in re.findall(
            r'<!--chunk starts -->(.*?)<!--chunk ends -->',
            doc.page_content,
            flags=re.DOTALL
        )
        if chunk.strip()
    ]
        chunk_names = []
        for i in range(len(chunks)):
            chunk_id = f"{document_id}_{i}"
            chunk_names.append(chunk_id)
            chunk_final = Document(
                            page_content = chunks[i],
                            metadata={
                "chunk_id": chunk_id,
                "document_id": document_id,
                "chunk_index": i,
                "source": source,
                "package": "BGLR"
            }
                                )

            logical_chunks.append(chunk_final)
        print(chunk_names)
        document_data = models.Documents(
            document_id=document_id,
            intro = intro,
            skills = skills,
            chunks=chunk_names,
        )

        db.add(document_data)
        db.commit()
except Exception as e:
    db.rollback()
    raise e
finally:
    db.close()



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



def retrieve_bglr_context(query, k=3):

    # 1. Retrieve relevant logical chunks
    results = vectorstore.similarity_search(
        query,
        k=k
    )

    retrieved_context = []

    # Avoid fetching the same document repeatedly
    document_cache = {}

    for chunk in results:
        print(chunk.metadata)

        document_id = chunk.metadata["document_id"]

        # 2. Fetch parent document information
        if document_id not in document_cache:

            row = db.query(models.Documents).filter(
                models.Documents.document_id == document_id
            ).first()


            if row:

                document_cache[document_id] = {
                    "intro": row.intro,
                    "skills": row.skills,
                    "related_chunks": row.chunks
                }

        # 3. Combine document and chunk information
        doc_info = document_cache.get(document_id)

        if doc_info:

            retrieved_context.append({

                "document_id": document_id,

                "intro": doc_info["intro"],

                "skills": doc_info["skills"],

                "related_chunks": doc_info["related_chunks"],

                "chunk": chunk.page_content,

                "chunk_metadata": chunk.metadata

            })

    db.close()

    return retrieved_context

query = "How do I fit a linear regression with fixed effects in BGLR?"

# context = retrieve_bglr_context(query, k=3)

# for item in context:

#     print("=" * 80)

#     print("\nINTRO:")
#     print(item["intro"])

#     print("\nSKILLS:")
#     print(item["skills"])

#     print("\RELATED CHUNKIDS:")
#     print(item["related_chunks"])

#     print("\nRETRIEVED CODE CHUNK:")
#     print(item["chunk"])

## Only get the single most similar document from the dataset
#retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

## Testing retrieval for a query
#query = "Can you please give me code for random regression using flat prior "

# results = retriever.invoke(query)

# for i,doc in enumerate(results):
#     print("=" * 80)
#     print(f"RESULT {i + 1}")
#     print(doc.page_content)
#     print(doc.metadata)