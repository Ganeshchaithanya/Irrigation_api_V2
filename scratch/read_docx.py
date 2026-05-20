import zipfile
import xml.etree.ElementTree as ET

def read_docx(file_path):
    print(f"Reading docx: {file_path}")
    try:
        with zipfile.ZipFile(file_path) as docx:
            xml_content = docx.read('word/document.xml')
            root = ET.fromstring(xml_content)
            
            # XML namespace for word processing ml
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            text_runs = []
            for para in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                para_text = []
                for run in para.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                    if run.text:
                        para_text.append(run.text)
                if para_text:
                    text_runs.append("".join(para_text))
            
            full_text = "\n".join(text_runs)
            print("Extracted Text Length:", len(full_text))
            
            # Print paragraphs containing "video" or "aspect" or "splash"
            keywords = ["video", "aspect", "ratio", "splash", "screen"]
            matching_paragraphs = []
            for p in text_runs:
                lower_p = p.lower()
                if any(kw in lower_p for kw in keywords):
                    matching_paragraphs.append(p)
                    
            print(f"Found {len(matching_paragraphs)} matching paragraphs:")
            for i, mp in enumerate(matching_paragraphs):
                print(f"{i+1}: {mp}")
                
    except Exception as e:
        print(f"Error reading docx: {e}")

if __name__ == '__main__':
    read_docx('AquaSol_Software_Design_v2.docx')
