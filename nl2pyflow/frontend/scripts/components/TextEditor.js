// TextEditor.js
function TextEditor({ text, onChange, onGenerate, isLoading }) {
  return (
    <div className="editor-container">
      <textarea
        className="text-editor"
        value={text}
        onChange={(e) => onChange(e.target.value)}
        placeholder={`Describe a single block here...

Example:
### Import Data
Loads data from CSV file and prepares the dataframe
`}
      />
      <button 
        className="generate-button" 
        onClick={onGenerate}
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <i className></i> Generation...
          </>
        ) : (
          <>
            <i className="fas fa-circle-play"></i> Generate Blocks
          </>
        )}
      </button>
    </div>
  );
}