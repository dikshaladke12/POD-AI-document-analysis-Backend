import json
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from FAX_POD.utils import decrypt_data, encrypt_data  # adjust import as needed

class AESMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # print(f"[AESMiddleware] Incoming {request.method} request to {request.path}")

        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body_unicode = request.body.decode('utf-8')
                # print(f"[AESMiddleware] Raw request body:\n{body_unicode}")

                json_data = json.loads(body_unicode)
                # print(f"[AESMiddleware] Parsed JSON request data:\n{json.dumps(json_data, indent=2)}")

                if "payload" in json_data:
                    decrypted = decrypt_data(json_data["payload"])
                    if decrypted:
                        # Inject into request._body so DRF re-parses it
                        request._body = json.dumps(decrypted).encode("utf-8")
                        # print("[AESMiddleware] ✅ Decryption successful. Injected into request._body")
                    else:
                        print("[AESMiddleware] ❌ Decryption returned None")
            except Exception as e:
                print("[AESMiddleware] Error processing request:", e)

    def process_response(self, request, response):
        # print(f"[AESMiddleware] Returning response for {request.path} with status {response.status_code}")
        try:
            if hasattr(response, 'data'):  # For DRF Response
                encrypted = encrypt_data(response.data)
                if encrypted:
                    return JsonResponse({"payload": encrypted}, status=response.status_code)
            elif hasattr(response, 'content'):
                # Optional: encrypt raw Django responses (e.g., not DRF)
                content = response.content.decode('utf-8')
                try:
                    parsed = json.loads(content)
                    encrypted = encrypt_data(parsed)
                    if encrypted:
                        return JsonResponse({"payload": encrypted}, status=response.status_code)
                except Exception as inner_e:
                    print("[AESMiddleware] Could not parse raw content as JSON:", inner_e)
        except Exception as e:
            print("[AESMiddleware] Error encrypting response:", e)

        return response