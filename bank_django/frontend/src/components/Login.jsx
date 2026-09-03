import { useEffect } from "react";

function getCSRFToken() {
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrftoken') {
          return value;
      }
  }
  return null;
}

const Login = () => {
  // Start video stream when the page loads
  useEffect(() => {
    const video = document.getElementById('video');

    // Access the camera
    navigator.mediaDevices.getUserMedia({ video: true })
      .then((stream) => {
        video.srcObject = stream;

        // Wait for video metadata to be loaded before accessing its dimensions
        video.onloadedmetadata = () => {
          // Log to confirm video stream is received
          console.log('Video stream started');
        };
      })
      .catch((err) => {
        console.error("Error accessing the camera: ", err);
      });
  }, []); // Empty dependency array ensures this runs only once when the component mounts

  const handleLogin = async () => {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');

    // Set canvas dimensions based on video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');
    
    // Draw the current video frame to the canvas
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert the canvas image to Base64
    const imageBase64 = canvas.toDataURL('image/jpeg').split(';base64,')[1]; // Only the Base64 part

    // Send the image to the server for authentication
    fetch('/api/login/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({ image: imageBase64 })
    })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          alert("Login successful!");
          window.location.href = '/loan-application'; // Redirect on success
        } else {
          alert("Authentication failed: " + data.error);
        }
      })
      .catch(err => console.error("Error during login: ", err));
  };

  return (
    <div>
      <h1>Facial Recognition Login</h1>
      <video id="video" autoPlay playsInline width="640" height="480"></video>
      <canvas id="canvas" style={{ display: 'none' }}></canvas>
      <button id="capture" onClick={handleLogin}>Login</button>
    </div>
  );
};

export default Login;
