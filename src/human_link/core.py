import uuid
import urllib.parse
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class LinkData:
    url: str
    session_id: str

def create(
    mode: str = "SEE", 
    primitives: Optional[List[str]] = None, 
    prompt: str = "",
    gateway: str = "https://agentcrowds.com/link"
) -> LinkData:
    """
    Generates a secure WebRTC link for the Human Link protocol.
    """
    session_id = str(uuid.uuid4())
    
    params = {"session": session_id, "mode": mode}
    if prompt:
        params["prompt"] = prompt
    if primitives:
        params["primitives"] = ",".join(primitives)
        
    url = f"{gateway}?{urllib.parse.urlencode(params)}"
    
    return LinkData(url=url, session_id=session_id)
