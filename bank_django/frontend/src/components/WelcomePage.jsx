import { useNavigate } from "react-router-dom";

const WelcomePage = () => {
  const navigate = useNavigate();

  const handleNavigateToSimulator = () => {
    navigate("/loan-simulator");
  };

  return (
    <div style={{ textAlign: "center", padding: "4rem 2rem", maxWidth: "560px", margin: "0 auto" }}>
      <h1>Welcome to Our Loan App</h1>
      <p>
        Explore our loan options with the simulator and easily apply for a loan
        that suits your needs.
      </p>
      <button
        onClick={handleNavigateToSimulator}
        style={{
          padding: "0.5rem 1rem",
          marginTop: "1rem",
          fontSize: "1rem",
          cursor: "pointer",
        }}
      >
        Go to Loan Simulator
      </button>
    </div>
  );
};

export default WelcomePage;
