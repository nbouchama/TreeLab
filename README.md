
TreeLab

TreeLab is an interactive desktop application for learning binary trees and binary search trees. It combines tree construction, animated algorithms, and a live visual representation to make data structures easier to explore.

Features

- Build arbitrary binary trees and binary search trees by hand, by insertion, or from generated examples.
- Explore preorder (RGD), inorder (GRD), postorder (GDR), reverse inorder (DRG), and breadth-first traversals.
- Animate searches, measurements, tree properties, insertion, deletion, and recursive calls.
- Inspect node values, parent/child links, levels, heights, and memory-style pointer views.
- Convert n-ary trees to binary trees using the left-child/right-sibling representation, with a step-by-step simulator.
- Create expression trees and red-black tree examples.
- Reposition nodes, zoom and pan the canvas, and open the tree view in full screen.
- Undo and redo tree edits; save and reopen trees as JSON files.
- Use the multiple-choice exercises and progressive challenges to practise tree concepts.

Requirements

- Python 3.8 or later
- Tkinter (included with most standard Python distributions)

Run


python treelab_en.py


On some Linux distributions, install the Tkinter package supplied by your Python distribution if it is not already available.

N-ary tree notation

Enter a node followed by its children in parentheses. Separate definitions with semicolons. For example:


A(B,C,D); B(E,F); C(G)


The simulator adds one binary link per step. The first child is attached on the left; each following sibling is attached on the right of the previous sibling.

Canvas controls

- Drag a node with the left mouse button to reposition it.
- Use the middle mouse button to pan the canvas.
- Hold Ctrl and use the mouse wheel to zoom; the toolbar also has zoom controls.
- Use the Full screen button to focus on the tree. Press Esc to return.
- Right-click the canvas or a node to open contextual actions.

Files

- treelab.py — French application
- treelab_en.py — English-language application
