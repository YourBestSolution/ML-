import os
import re
import pdfplumber

current_file_folder = os.getcwd()
docs_folder = os.path.join(current_file_folder, "docs")
text_folder = os.path.join(current_file_folder, "text")
output_file = os.path.join(current_file_folder, "merged.txt")

if not os.path.exists(text_folder):
    os.makedirs(text_folder)
    
def clean_text(text):
    text = re.sub(r'\(cid:\d+\)', '', text)  
    text = re.sub(r'‡|‰|‚,|', '', text)
    text = re.sub(r'[^\S\r\n]+', ' ', text)  
    text = re.sub(r'ﬂ|ﬁ', '', text)
    text = re.sub(r'–', '-', text)
    return text

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print(f"ERR {pdf_path}: {e}")
    return text

def convert_pdf_to_text(docs_folder, text_folder):
    pdf_files = [f for f in os.listdir(docs_folder) if f.endswith(".pdf") and os.path.isfile(os.path.join(docs_folder, f))]

    for file in pdf_files:
        txt_filename = os.path.join(text_folder, f"{os.path.splitext(file)[0]}.txt")
        if os.path.exists(txt_filename):
            print(f"SKIP {file}")
        else:
            try:
                text = extract_text_from_pdf(os.path.join(docs_folder, file))
                text = clean_text(text)
                with open(txt_filename, "w", encoding="utf-8") as txt_file:
                    txt_file.write(text)
                print(f"TXT {file}")
            except Exception as e:
                print(f"ERR {file}: {e}")

def copy_txt_files(docs_folder, text_folder):
    txt_files = [f for f in os.listdir(docs_folder) if f.endswith(".txt") and os.path.isfile(os.path.join(docs_folder, f))]

    for file in txt_files:
        dest_file = os.path.join(text_folder, file)
        if os.path.exists(dest_file):
            print(f"SKIP {file}")
        else:
            try:
                with open(os.path.join(docs_folder, file), "r", encoding="utf-8") as src_file:
                    text = src_file.read()
                    text = clean_text(text)
                    with open(dest_file, "w", encoding="utf-8") as dest_file:
                        dest_file.write(text)
                print(f"COPY {file}")
            except Exception as e:
                print(f"ERR {file}: {e}")

def combine_txt_files(text_folder, output_file):
    txt_files = [f for f in os.listdir(text_folder) if f.endswith(".txt") and os.path.isfile(os.path.join(text_folder, f))]

    with open(output_file, "w", encoding="utf-8") as merged_file:
        for file in txt_files:
            try:
                with open(os.path.join(text_folder, file), "r", encoding="utf-8") as txt_file:
                    text = txt_file.read()
                    merged_file.write(text)
                merged_file.write("\n")
            except Exception as e:
                print(f"ERR {file}: {e}")

    print(f"MERGED {output_file}")

convert_pdf_to_text(docs_folder, text_folder)
copy_txt_files(docs_folder, text_folder)
combine_txt_files(text_folder, output_file)