from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient

app = Flask(__name__)
CORS(app) # Frontend se connect karne ke liye zaruri hai

# Database connection caching ke liye
client = MongoClient('mongodb+srv://Krishna:pss968048@cluster0.4rfuzro.mongodb.net/?retryWrites=true&w=majority')
db = client['shiksha_vibhag_db']
collection = db['student_results']

# Official board ki site ka form URL (Isko apne hisaab se replace karna)
TARGET_URL = "http://official-board-site.com/result-endpoint" 

def scrape_result(roll_no, year, std):
    # Step 1: Pehle DB mein check karo, taaki official site par baar-baar load na pade
    existing_data = collection.find_one({"roll_no": roll_no, "year": year, "class": std}, {"_id": 0})
    if existing_data:
        return existing_data

    # Step 2: Agar DB mein nahi hai, toh Live Scrape karo
    session = requests.Session()
    
    # Ye wahi details hain jo original site ke form mein submit hoti hain
    payload = {
        'roll_number': roll_no, 
        'year': year, 
        'class': std, 
        'submit_btn': 'Search'
    }
    
    # Browser jaisa dikhne ke liye headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = session.post(TARGET_URL, data=payload, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')

        # === HTML Parsing Logic ===
        # Note: id ya class name (jaise 'student_name') target site ke HTML source code se match karne honge.
        
        extracted_name = soup.find(id='student_name').text.strip() if soup.find(id='student_name') else "N/A"
        extracted_father_name = soup.find(id='father_name').text.strip() if soup.find(id='father_name') else "N/A"
        total_marks = soup.find(id='total_marks').text.strip() if soup.find(id='total_marks') else "N/A"
        final_result = soup.find(class_='result-status').text.strip() if soup.find(class_='result-status') else "N/A"

        # Final JSON Structure
        result_data = {
            "roll_no": roll_no,
            "year": year,
            "class": std,
            "Name": extracted_name,
            "Father Name": extracted_father_name,
            "Total_Marks": total_marks,
            "Result": final_result
        }

        # Step 3: DB mein save karo next time ke liye
        collection.insert_one(result_data.copy())
        
        # Object ID frontend ko nahi bhejni, isliye hata do
        if "_id" in result_data:
            del result_data["_id"]

        return result_data

    except Exception as e:
        return {"error": "Scraping failed or site down", "details": str(e)}

# Frontend is endpoint par POST request bhejega
@app.route('/api/fetch_result', methods=['POST'])
def fetch_result():
    data = request.json
    roll_no = data.get('roll_no')
    year = data.get('year')
    std = data.get('class')

    if not roll_no:
        return jsonify({"error": "Roll number is required"}), 400

    # Scrape function call karo
    result = scrape_result(roll_no, year, std)
    return jsonify(result)

if __name__ == '__main__':
    # Server par external access ke liye 0.0.0.0 par run karein
    app.run(host='0.0.0.0', port=5000, debug=True)

