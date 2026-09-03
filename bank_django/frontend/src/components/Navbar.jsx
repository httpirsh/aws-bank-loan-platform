import { Link } from "react-router-dom";

const Navbar = () => {
  return (
    <nav style={{ margin: "1rem" }}>
      <Link to="/login" style={{ marginRight: "1rem" }}>Login</Link>
      <Link to="/loan-simulator">Loan Simulator</Link>
    </nav>
  );
};

export default Navbar;
