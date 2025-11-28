// CodeModal.js
function CodeModal({ block, code, isEditing, onClose, onEdit, onSave, onChange }) {
    return (
        <>
            <div className="modal-overlay" onClick={onClose}></div>
            <div className="code-modal">
                <div className="code-modal-header">
                    <h3>
                        <i className="fas fa-code"></i> 
                        {block.title} - Step {block.step}
                        <span className="code-language-badge">Python</span>
                    </h3>
                    <button className="close-button" onClick={onClose}>×</button>
                </div>
                <div className="code-modal-content">
                    {isEditing ? (
                        <textarea 
                            className="code-editor"
                            value={code}
                            onChange={(e) => onChange(e.target.value)}
                            spellCheck="false"
                        />
                    ) : (
                        <div className="code-display-container">
                            <pre className="code-display">{code}</pre>
                            <div className="code-signature">
                                <span className="code-function">def</span> {block.id}(
                                <span className="code-param">context: dict</span>)  
                                <span className="code-return">dict</span>:
                            </div>
                        </div>
                    )}
                </div>
                <div className="code-modal-footer">
                    {isEditing ? (
                        <button className="save-button" onClick={onSave}>
                            <i className="fas fa-save"></i> Save Changes
                        </button>
                    ) : (
                        <button className="edit-button" onClick={onEdit}>
                            <i className="fas fa-edit"></i> Edit Code
                        </button>
                    )}
                </div>
            </div>
        </>
    );
  }
  