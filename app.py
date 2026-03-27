from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

client = MongoClient('mongodb+srv://Krishna:pss968048@cluster0.4rfuzro.mongodb.net/?retryWrites=true&w=majority')
db = client['shiksha_vibhag_db']
collection = db['student_results']

TARGET_URL = "http://official-board-site.com/result-endpoint" 

def scrape_result(roll_no, year, std):
    existing_data = collection.find_one({"roll_no": roll_no, "year": year, "class": std}, {"_id": 0})
    if existing_data:
        return existing_data

    session = requests.Session()
    payload = {'roll_number': roll_no, 'year': year, 'class': std, 'submit_btn': 'Search'}
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = session.post(TARGET_URL, data=payload, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')

        # === Basic Info Extraction ===
        extracted_name = soup.find(id='student_name').text.strip() if soup.find(id='student_name') else "N/A"
        extracted_father_name = soup.find(id='father_name').text.strip() if soup.find(id='father_name') else "N/A"
        total_marks = soup.find(id='total_marks').text.strip() if soup.find(id='total_marks') else "N/A"
        final_result = soup.find(class_='result-status').text.strip() if soup.find(class_='result-status') else "N/A"

        # === DYNAMIC SUBJECTS EXTRACTION ===
        # Assuming subjects are in a table with rows having class 'subject-row'
        subjects_data = {}
        marks_rows = soup.find_all('tr', class_='subject-row')
        for row in marks_rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                sub_name = cols[0].text.strip()
                sub_marks = cols[1].text.strip()
                subjects_data[sub_name] = sub_marks
                
        # [DUMMY DATA FOR TESTING] - Agar target site par abhi script test kar rahe ho aur table nahi mili:
        if not subjects_data:
            subjects_data = {"Hindi": "85", "English": "78", "Physics": "82", "Chemistry": "90", "Maths": "95"}

        # Final JSON Structure (Strictly labeling Name and Father Name)
        result_data = {
            "roll_no": roll_no,
            "year": year,
            "class": std,
            "Name": extracted_name,
            "Father Name": extracted_father_name,
            "Subjects": subjects_data, # Naya Field
            "Total_Marks": total_marks,
            "Result": final_result
        }

        collection.insert_one(result_data.copy())
        if "_id" in result_data:
            del result_data["_id"]

        return result_data

    except Exception as e:
        return {"error": "Scraping failed", "details": str(e)}

@app.route('/api/fetch_result', methods=['POST'])
def fetch_result():
    data = request.json
    roll_no = data.get('roll_no')
    if not roll_no:
        return jsonify({"error": "Roll number is required"}), 400
    
    return jsonify(scrape_result(roll_no, data.get('year'), data.get('class')))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    
