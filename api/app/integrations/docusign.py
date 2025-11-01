"""DocuSign e-signature integration (PR#10)"""

from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition
from typing import List, Dict

class DocuSignClient:
    """DocuSign integration for document signing"""
    
    def __init__(self, access_token: str, account_id: str, base_url: str):
        self.api_client = ApiClient()
        self.api_client.host = base_url
        self.api_client.set_default_header("Authorization", f"Bearer {access_token}")
        self.account_id = account_id
    
    def create_envelope(
        self,
        document_path: str,
        signers: List[Dict],
        subject: str,
        email_body: str
    ) -> str:
        """Create signing envelope
        
        Args:
            document_path: Path to PDF document
            signers: List of signers with email, name, tabs
            subject: Email subject
            email_body: Email body text
            
        Returns:
            Envelope ID
        """
        envelopes_api = EnvelopesApi(self.api_client)
        
        # Create envelope definition
        envelope_definition = EnvelopeDefinition(
            email_subject=subject,
            email_blurb=email_body,
            documents=[{
                "document_id": "1",
                "name": "Contract",
                "file_extension": "pdf",
                "document_base64": self._read_file_base64(document_path)
            }],
            recipients={"signers": signers},
            status="sent"
        )
        
        result = envelopes_api.create_envelope(
            self.account_id,
            envelope_definition=envelope_definition
        )
        
        return result.envelope_id
    
    def get_envelope_status(self, envelope_id: str) -> Dict:
        """Get envelope status
        
        Returns:
            {"status": "sent|delivered|completed|declined|voided"}
        """
        envelopes_api = EnvelopesApi(self.api_client)
        envelope = envelopes_api.get_envelope(self.account_id, envelope_id)
        return {"status": envelope.status}
    
    def download_signed_document(self, envelope_id: str) -> bytes:
        """Download signed document"""
        envelopes_api = EnvelopesApi(self.api_client)
        documents = envelopes_api.get_document(
            self.account_id, 
            envelope_id, 
            "combined"
        )
        return documents
    
    def _read_file_base64(self, path: str) -> str:
        """Read file and encode as base64"""
        import base64
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
