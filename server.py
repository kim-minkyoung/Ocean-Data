from flask import Flask, request, jsonify
from llm import *
import pickle

app = Flask(__name__)

# 임베딩 설정
model_path = "intfloat/multilingual-e5-base"
model_kwargs = {'device': 'cuda'}
encode_kwargs = {'normalize_embeddings': True}
embeddings = HuggingFaceEmbeddings(
    model_name=model_path,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs
)
db = None
rag_chain = None

# LLM 설정
llm = setup_llm_pipeline()

@app.route('/', methods=['GET'])
def home():
    return "Hello, World!"

@app.route('/greet', methods=['GET'])
def greet():
    name = request.args.get('name', 'Guest')
    return jsonify(message=f"Hello, {name}!")

@app.route('/data', methods=['GET'])
def get_data():
    data = {
        'message': 'Hello from Flask!',
        'value': 5454546
    }
    return jsonify(data)

@app.route('/setup', methods=['POST'])
def setup():
    global db, rag_chain

    data = request.get_json()
    category  = data.get('category')
    species = data.get('species')

    if db is None:
        faiss_db_directory = "./faiss/" + category + "/" + species

        # 빈 docstore와 index_to_docstore_id 생성
        with open(faiss_db_directory + "_index_to_docstore_id.pkl", "rb") as f:
            index_to_docstore_id = pickle.load(f)

        with open(faiss_db_directory + "_docstore.pkl", "rb") as f:
            docstore = pickle.load(f)

        # 인덱스 로드 및 FAISS 초기화
        index = faiss.read_index(faiss_db_directory + "_faiss_db.index")
        db = FAISS(
            embedding_function=embeddings,
            index=index,
            docstore=docstore,
            index_to_docstore_id=index_to_docstore_id
        )

    retriever = db.as_retriever(search_type="mmr", search_kwargs={'k': 3, 'fetch_k': 8})
    rag_chain = rag(retriever, llm)

    return jsonify({"message": "FAISS DB initialized successfully"})


@app.route('/ask', methods=['POST'])
def ask():
    global rag_chain

    torch.cuda.empty_cache()

    data = request.get_json()
    question = data.get('question')

    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    response = rag_chain.invoke(question)
    return jsonify(response)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)  # 모든 네트워크 인터페이스에서 접근 가능하게 설정
