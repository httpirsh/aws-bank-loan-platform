import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import WelcomePage from "./components/WelcomePage";
import LoanSimulator from "./components/LoanSimulator";
import Login from "./components/Login";
import LoanApplication from "./components/LoanApplication";

function App() {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<WelcomePage />} />
        <Route path="/loan-simulator" element={<LoanSimulator />} />
        <Route path="/login" element={<Login />} />
        <Route path="/loan-application" element={<LoanApplication />} />
      </Routes>
    </Router>
  );
}

export default App;
