from docx import Document
path = r'F:\Nouveau dossier\StashMaster_Corrections_Prompts.docx'
try:
    doc = Document(path)
    for para in doc.paragraphs:
        print(para.text)
except Exception as e:
    print('ERROR', e)
