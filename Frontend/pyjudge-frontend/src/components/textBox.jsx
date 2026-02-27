function TextBox({ value, onChange }) {
  return (
    <textarea
      className="prompt-form"
      rows={4}
      placeholder="Write a prompt for Google Gemini:"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

export default TextBox;
