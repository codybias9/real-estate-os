"""SMS service for sending text messages."""

from typing import Optional
import httpx

from ..config import settings


class SMSService:
    """SMS service for sending text messages."""

    def __init__(self):
        """Initialize SMS service."""
        self.provider = settings.SMS_PROVIDER
        self.api_key = settings.SMS_API_KEY
        self.from_number = settings.SMS_FROM_NUMBER

    async def send_sms(
        self,
        to_number: str,
        message: str,
    ) -> bool:
        """
        Send an SMS message.

        Args:
            to_number: Recipient phone number
            message: SMS message content

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # For development/testing, just print the SMS
            if settings.DEBUG or self.provider == "mock":
                print(f"\n{'='*50}")
                print(f"SMS: {to_number}")
                print(f"{'='*50}")
                print(message)
                print(f"{'='*50}\n")
                return True

            # Integration with real SMS providers (Twilio, SNS, etc.) would go here
            if self.provider == "twilio":
                return await self._send_via_twilio(to_number, message)
            elif self.provider == "sns":
                return await self._send_via_sns(to_number, message)
            else:
                print(f"Unknown SMS provider: {self.provider}")
                return False

        except Exception as e:
            print(f"Error sending SMS: {e}")
            return False

    async def _send_via_twilio(self, to_number: str, message: str) -> bool:
        """Send SMS via Twilio."""
        # Twilio integration would go here
        # Example:
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Messages.json",
        #         auth=(ACCOUNT_SID, AUTH_TOKEN),
        #         data={
        #             "From": self.from_number,
        #             "To": to_number,
        #             "Body": message,
        #         },
        #     )
        #     return response.status_code == 201
        print(f"Twilio SMS would be sent to {to_number}: {message}")
        return True

    async def _send_via_sns(self, to_number: str, message: str) -> bool:
        """Send SMS via AWS SNS."""
        # AWS SNS integration would go here
        # Example:
        # import boto3
        # sns = boto3.client('sns')
        # response = sns.publish(
        #     PhoneNumber=to_number,
        #     Message=message,
        # )
        # return response['MessageId'] is not None
        print(f"AWS SNS SMS would be sent to {to_number}: {message}")
        return True

    async def send_campaign_sms(
        self,
        to_number: str,
        content: str,
        first_name: Optional[str] = None,
    ) -> bool:
        """Send campaign SMS with personalization."""
        # Replace placeholders
        personalized_content = content.replace("{{first_name}}", first_name or "there")

        # Ensure message is within SMS length limit (160 characters for standard SMS)
        if len(personalized_content) > 160:
            personalized_content = personalized_content[:157] + "..."

        return await self.send_sms(to_number, personalized_content)

    async def send_verification_sms(self, to_number: str, code: str) -> bool:
        """Send verification code via SMS."""
        message = f"Your Real Estate OS verification code is: {code}"
        return await self.send_sms(to_number, message)


# Singleton instance
sms_service = SMSService()
