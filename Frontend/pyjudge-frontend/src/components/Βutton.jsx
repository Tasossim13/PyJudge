function Button({ onClick }) {
  return (
    <button className="btn btn-primary mt-3" onClick={onClick}>
      Send Prompt
    </button>
  );
}

export default Button;
