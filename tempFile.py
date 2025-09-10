# import requests
# import tempfile

# def fetch_and_save_fax_pdf(body_data):
#     import requests
#     import tempfile

#     try:
#         response = requests.post("https://api.faxage.com/httpsfax.php", data=body_data)

#         # Accept 'application/pdf' or generic binary stream
#         content_type = response.headers.get("Content-Type", "")
#         if "pdf" in content_type or "application/octet-stream" in content_type or response.content.startswith(b"%PDF"):
#             with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="fax_", mode="wb") as temp_pdf:
#                 temp_pdf.write(response.content)
#                 temp_pdf.flush()
#                 print(f"✅ Fax PDF saved at: {temp_pdf.name}")
#                 return temp_pdf.name
#         else:
#             print(f"❌ Unexpected response code: {response.status_code}")
#             print("❌ Response text (preview):", response.text[:200])  # Avoid flooding terminal
#             return None

#     except Exception as e:
#         print(f"❌ Error fetching or saving fax: {e}")
#         return None



# body = {
#     "username": "",
#     "company": "",
#     "password": "",
#     "operation": "getfax",
#     "faxid": "575497833",   # obtained from listfax
#     "informat": "pdf"
# }

# pdf_path = fetch_and_save_fax_pdf(body)
