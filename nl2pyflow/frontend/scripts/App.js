// Main App Components
function App() {
  const [blocks, setBlocks] = React.useState([]);
  const [inputText, setInputText] = React.useState('');
  const [selectedBlock, setSelectedBlock] = React.useState(null);
  const [blockCode, setBlockCode] = React.useState('');
  const [isEditing, setIsEditing] = React.useState(false);
  const [jsPlumbInstance, setJsPlumbInstance] = React.useState(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [leftPanelWidth, setLeftPanelWidth] = React.useState(25); // Initial percentage left panel
  const [isDragging, setIsDragging] = React.useState(false);
  
  React.useEffect(() => {
    if (typeof jsPlumb !== 'undefined') {
      const instance = jsPlumb.getInstance({
        ConnectionsDetachable: true,
        Connector: ["Bezier", { curviness: 100 }],
        Endpoint: ["Dot", { radius: 7 }],
        EndpointStyle: { fill: "#4CAF50" },
        PaintStyle: { 
          stroke: "#4CAF50", 
          strokeWidth: 3 
        },
        HoverPaintStyle: { 
          stroke: "#2E7D32", 
          strokeWidth: 4 
        },
        ConnectionOverlays: [
          ["Arrow", { 
            location: 1,
            width: 12,
            length: 12,
            foldback: 0.8
          }]
        ]
      });
      
      setJsPlumbInstance(instance);
      
      return () => {
        instance.reset();
      };
    }
  }, []);
  
  const generateBlocks = async () => {
  if (!inputText.trim()) {
    setError('Enter text to generate a block');
    return;
  }

  setIsLoading(true);
  setError(null);

  try {
    // 1. First we parse the blocks
    const parseResponse = await fetch('http://localhost:5000/api/parse-blocks', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text: inputText }),
    });

    const parseData = await parseResponse.json();

    if (!parseData.success || !parseData.blocks || parseData.blocks.length === 0) {
      throw new Error(parseData.error || 'No block detected in input');
    }

    const block = parseData.blocks[0];  // Usa solo il primo blocco

    // For each block, we generate the code
    const codeResponse = await fetch('http://localhost:5000/api/generate-code', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ block }),
    });

    const codeData = await codeResponse.json();

    const newBlock = {
      id: block.name,
      title: block.title,
      description: block.description,
      step: blocks.length + 1,
      type: determineBlockType(block.title, block.description),
      x: 100 + ((blocks.length % 2) * 300),
      y: 100 + Math.floor(blocks.length / 2) * 200,
      code: codeData.success ? codeData.code : `# Default code for ${block.title}\n\ndef ${block.name}(context: dict) -> dict:\n    # ${block.description}\n    return context`
    };

    const updatedBlocks = [...blocks, newBlock];
    setBlocks(updatedBlocks);
    setInputText(''); // Clean the texteditor
    createConnections(updatedBlocks);

  } catch (err) {
    setError(err.message);
    console.error('Error in block generation:', err);
  } finally {
    setIsLoading(false);
  }
};

  // Determines block type based on title/description
  const determineBlockType = (title, description) => {
    const lowerTitle = title.toLowerCase();
    const lowerDesc = description.toLowerCase();
    
    if (/data|load|read|import/i.test(lowerTitle) || /file|csv|json|database/i.test(lowerDesc)) {
      return 'data';
    } else if (/model|train|predict|ml|machine learning/i.test(lowerTitle)) {
      return 'model';
    } else if (/output|result|report|visualization/i.test(lowerTitle)) {
      return 'output';
    } else {
      return 'process';
    }
  };

  // Creates connections between blocks in sequential order
  const createConnections = (blocks) => {
    setTimeout(() => {
      if (jsPlumbInstance) {
        jsPlumbInstance.deleteEveryConnection();

        for (let i = 0; i < blocks.length - 1; i++) {
          const sourceId = `block-${blocks[i].id}`;
          const targetId = `block-${blocks[i+1].id}`;
          
          if (document.getElementById(sourceId) && document.getElementById(targetId)) {
            jsPlumbInstance.connect({
              source: sourceId,
              target: targetId,
              anchor: ["Bottom", "Top"],
            });
          }
        }
      }
    }, 200);
  };
  
  const handleEditBlock = (block) => {
    setSelectedBlock(block);
    setBlockCode(`# Code for ${block.title}\n\ndef ${block.title.toLowerCase().replace(/ /g, '_')}():\n    # Implementation for ${block.description}\n    print("Block execution ${block.step}")\n    pass`);
    setIsEditing(false);
  };
  
  const handleVerifyBlock = (block) => {
    alert(`Block verification "${block.title}" successfully completed!`);
  };
  
  const handleCloseModal = () => {
    setSelectedBlock(null);
    setIsEditing(false);
  };
  
  const handleEditCode = () => {
    setIsEditing(true);
  };
  
  const handleSaveCode = () => {
    setIsEditing(false);
    
    const updatedBlocks = blocks.map(b => {
      if (b.id === selectedBlock.id) {
        return {...b, code: blockCode};
      }
      return b;
    });
    
    setBlocks(updatedBlocks);
    alert(`Code for "${selectedBlock.title}" successfully saved!`);
  };

  const handleMouseDown = (e) => {
    setIsDragging(true);
    document.body.style.cursor = 'col-resize';
    e.preventDefault();
  };
  
  const handleMouseMove = (e) => {
    if (!isDragging) return;
    
    const appWidth = document.querySelector('.app').offsetWidth;
    const newWidth = (e.clientX / appWidth) * 100;
    
    // Limit the width between 20% and 50%
    setLeftPanelWidth(Math.min(Math.max(newWidth, 20), 50));
  };
  
  const handleMouseUp = () => {
    setIsDragging(false);
    document.body.style.cursor = '';
  };
  
  // Add event listeners
  React.useEffect(() => {
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);
  
  return (
    <div className="app">
      <div 
          className="left-panel" 
          style={{ width: `${leftPanelWidth}%` }}
        >
          <div 
            className="resize-handle" 
            onMouseDown={handleMouseDown}
          ></div>
          
          <div className="editor-container">
            <TextEditor 
              text={inputText} 
              onChange={(text) => {
                setInputText(text);
                setError(null);
              }} 
              onGenerate={generateBlocks}
              isLoading={isLoading}
            />
            {error && <div className="error-message">{error}</div>}
          </div>
      </div>
      <div className="right-panel">
        {jsPlumbInstance && (
          <FlowChart 
            blocks={blocks} 
            jsPlumbInstance={jsPlumbInstance}
            onEdit={handleEditBlock}
            onVerify={handleVerifyBlock}
          />
        )}
      </div>
      
      {selectedBlock && (
        <CodeModal 
          block={selectedBlock}
          code={selectedBlock?.code || ''}
          isEditing={isEditing}
          onClose={handleCloseModal}
          onEdit={handleEditCode}
          onSave={handleSaveCode}
          onChange={setBlockCode}
        />
      )}
    </div>
  );
}

ReactDOM.render(<App />, document.getElementById('root'));