import com.google.gson.JsonObject; // allows us to acsess values by finding their keys
import com.google.gson.JsonParser; // reads and understand the JSON text
import javax.swing.*; // imports all GUI stuff we want buttons, interface etc.
import java.awt.*; // helps with GUI fonts, colours and layout
import java.net.URI; // we use it to tell java where the backend is
import java.net.http.HttpRequest; // whats actually being sent from java
import java.net.http.HttpResponse; // what flask responds with

// this is the window that pops up when you click message seller
public class MessageWindow extends JDialog {

    private final int listingID; // we need the listing id to start the conversation
    private int conversationID = -1; // -1 means we haven't started the chat yet. once we send a message flask gives us the real id
    
    private final JTextArea chatArea = new JTextArea(); // where the messages show up
    private final JTextField messageField = new JTextField(20); // where you type the message
    private final JButton sendButton = new JButton("Send"); // button to send

    // Constructor: creates the chat window
    public MessageWindow(JFrame parent, int listingID, String sellerName, String itemTitle) {
        super(parent, "Chat with " + sellerName + " about " + itemTitle, false); // names the window
        this.listingID = listingID;

        setSize(400, 500); // size of the popup
        setLocationRelativeTo(parent); // centres it
        setLayout(new BorderLayout(10, 10)); // organizes the screen

        // setting up the chat display
        chatArea.setEditable(false); // users cant type in the history box
        chatArea.setLineWrap(true); // moves to next line if text is too long
        chatArea.setWrapStyleWord(true); // keeps whole words together
        add(new JScrollPane(chatArea), BorderLayout.CENTER); // adds scrollbar and puts it in the middle

        // setting up the bottom area where you type
        JPanel bottomPanel = new JPanel(new BorderLayout(5, 5));
        bottomPanel.add(messageField, BorderLayout.CENTER);
        bottomPanel.add(sendButton, BorderLayout.EAST);
        add(bottomPanel, BorderLayout.SOUTH);

        // when you click send or press enter it sends the message
        sendButton.addActionListener(e -> sendMessage());
        messageField.addActionListener(e -> sendMessage());
        
        chatArea.setText("Send a message to start the conversation.\n"); // starting text
    }

    // sending the message to flask
    private void sendMessage() {
        String text = messageField.getText().trim(); // get what they typed and remove extra spaces
        if (text.isEmpty()) return; // if its empty do nothing

        messageField.setText(""); // wipe the text box
        chatArea.append("You: " + text + "\n\n"); // show it on our screen instantly
        
        // doing this in the background so the window doesnt freeze
        new SwingWorker<Void, Void>() {
            @Override
            protected Void doInBackground() throws Exception {
                JsonObject data = new JsonObject();
                data.addProperty("body", text); // flask expects the key to be "body"

                // if we dont have a conversation yet we use the listing url. if we do we use the conversation url
                String url = (conversationID == -1) 
                        ? "http://127.0.0.1:5000/api/listings/" + listingID + "/messages"
                        : "http://127.0.0.1:5000/api/conversations/" + conversationID + "/messages";

                // building the message to send to flask
                HttpRequest request = HttpRequest.newBuilder(URI.create(url))
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(data.toString()))
                        .build();

                // sending it and getting the response
                HttpResponse<String> response = ApiClient.client.send(request, HttpResponse.BodyHandlers.ofString());
                
                // if flask says it worked and it was our first message
                if (response.statusCode() == 201 && conversationID == -1) {
                    // flask sends back the new conversation id so we save it for next time
                    JsonObject res = JsonParser.parseString(response.body()).getAsJsonObject();
                    conversationID = res.get("conversation_id").getAsInt();
                } else if (response.statusCode() == 400) {
                    // if the user tried to message themselves or it failed, show the error
                    SwingUtilities.invokeLater(() -> chatArea.append("System Error: " + response.body() + "\n"));
                }
                return null;
            }
        }.execute();
    }
}