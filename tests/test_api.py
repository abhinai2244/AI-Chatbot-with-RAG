import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.anyio
async def test_chat_endpoint(client):
    # Mock the service layer to test API contract only
    with patch("app.api.routes.process_chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "Hello from AI"
        
        response = await client.post("/api/chat", json={"query": "Hi", "session_id": "123"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Hello from AI"
        assert data["session_id"] == "123"
        mock_chat.assert_called_once()

@pytest.mark.anyio
async def test_upload_endpoint(client):
    # Mock the service layer
    with patch("app.api.routes.process_file", new_callable=AsyncMock) as mock_file:
        # Mock UploadFile content
        files = {'file': ('test.txt', b'content', 'text/plain')}
        data = {'session_id': '123'}
        
        response = await client.post("/api/upload", files=files, data=data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.txt"
        assert "successfully" in data["message"]
        mock_file.assert_called_once()
