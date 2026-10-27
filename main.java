
import com.google.gson.JsonElement; // holds the JSON info in java
import com.google.gson.JsonObject; // allows us to acsess values by finding their keys
import com.google.gson.JsonParser; // reads and understand the JSON text
import javax.swing.*;  // imports all GUI stuff we want buttons, interface etc.
import javax.swing.table.DefaultTableModel; // table component adds the data in the rows, columns etc.
import java.awt.*; // helps with GUI fonts, colours and layout
import java.awt.event.MouseAdapter; // allows mouse controls
import java.awt.event.MouseEvent; // how the mouse was used like clicking amount etc.
import java.net.URI; // we use it to tell java where the backend is
import java.net.URLEncoder; // translates into allowed computer format from regular typing
import java.net.http.HttpClient; // messanger between our java file and flask
import java.net.http.HttpRequest; // whats actually being sent from java
import java.net.http.HttpResponse; // what flask responds with
import java.nio.charset.StandardCharsets;// translates into computer language human text
import java.time.Duration; // time limit that java allows flask to respond
import java.util.ArrayList; // tools from data structures that allow organaizng and storing data
import java.util.List;//
import java.util.Locale;// handles regional fromats currency, time etc.


// this is where the window the popup is GUI and everything is being built
public class main extends JFrame {  // JFrame is the window that pops up when we run


    // Address of our Flask backend
    private static final String API_URL =
            "http://127.0.0.1:5000/api/listings"; // creating an apiurl variable so we dont have to keep getting the url

    // Search bar and buttons
    private final JTextField searchField = new JTextField(22); // creating the search bar for people to type
    private final JButton searchButton = new JButton("Search"); // search excution button
    private final JButton refreshButton = new JButton("Refresh"); // refresh button
    private final JLabel statusLabel = new JLabel("Ready"); // status label tells user whats happening whats being found or not
// none of these are programmed to do anything yet. Just starting off by creating the buttons


    // Table that displays products
    private final DefaultTableModel tableModel =
            new DefaultTableModel(
                    new String[]{
                            "Item",
                            "Price",
                            "Category",
                            "Condition",
                            "Seller"
                    }, 0) {
    // we are making the bones of the table the columns are being made and then the info will be added later

                @Override // in the default table model there is a variable called isCellEditable. this usually displays true so people can edit we are making it false
                public boolean isCellEditable(int row, int column) {
                    return false;
                }
            }; // we are making it so that the table is read only so that users cannot just change prices of stuff
    

    private final JTable table = new JTable(tableModel); // now we are creating the what the user will see

    private List<Listing> displayedListings = new ArrayList<>(); // here we are creating a list of listings in displayedlistings and creating an empty arraylist

    // Constructor: creates the marketplace window
    public main() {

        super("Lakehead Students Shop"); // calls jframe to build our window called lakehead students shop

        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE); // X buttons closes window
        setSize(900, 500); // popup window size
        setLocationRelativeTo(null); // centering the window on screen by saying null, no reference so just centre it
        setLayout(new BorderLayout(10, 10)); // sets the spacing between the 5 areas on the screen by 10 pixels horizontally and vertically

        // Create the heading using the JLabel compnent of the swing library
        JLabel heading = new JLabel(
                "Lakehead Students Shop - Browse Listings"
        );

        heading.setFont(
                new Font("Arial", Font.BOLD, 20) // set the foint to ariel bold it and change the size
        );

        // Create a panel that will hold our search controls
        JPanel controls = new JPanel(
                new FlowLayout(FlowLayout.LEFT) // going from left to write
        );

        controls.add(new JLabel("Find an item:")); // text beside search bar
        controls.add(searchField); // adds our created search bar
        controls.add(searchButton); // adds our search button
        controls.add(refreshButton); // adds our refresh button

        // Add heading and search controls into one container at the top so we can organize where each part goes in that box
        JPanel top = new JPanel(new BorderLayout(0, 8));
        // moving the top container we made to the top of the window
         add(top, BorderLayout.NORTH);
        // tiile at the top of the box
        top.add(heading, BorderLayout.NORTH);
        // 8 pixels below we have the controls. so we built the box so we can adjust hwere these go with more ease
        top.add(controls, BorderLayout.SOUTH);

       

        // Adjusting marketplace table
        table.setRowHeight(28); // making it 28 pixels high 

        table.setSelectionMode(
                ListSelectionModel.SINGLE_SELECTION // you can only click one item at a time. if you clicked item a then item b only item b is now clicked
        );

        table.getTableHeader().setReorderingAllowed(false); //you cant move columns around anymore

        add(new JScrollPane(table), BorderLayout.CENTER); // makes a scroll bar and centres the table

        //  the Status message we created is placed at bottom
        add(statusLabel, BorderLayout.SOUTH);

        // Search button functioanlity. When clicked it will call the loadlisting function
        searchButton.addActionListener(e -> loadListings());

        // Pressing Enter also searches instead of having to always press search
        searchField.addActionListener(e -> loadListings());

        // Refresh clears search and reloads listings
        refreshButton.addActionListener(e -> { // when refresh clicked
            searchField.setText(""); // search bar wiped
            loadListings(); // and we load the listings
        });

        // we are adding mouse functionality. when a user does something with the mouse we tell java to listen to it
        table.addMouseListener(new MouseAdapter() {

            @Override // using MouseAdapter we are overriding how mouseClicked is gonna work
            public void mouseClicked(MouseEvent e) { // when mouse is clicked we are gonna do stuff

                if (e.getClickCount() == 2) { // if clicked twice

                    int row = table.getSelectedRow(); // get the selected row

                    if (row >= 0 && // if row is greater than 0 because we start at 0 and less would mean none is selected
                            row < displayedListings.size()) { // if row is less than the amount of listings we have

                        showListing(displayedListings.get(row)); // Gets the selected product from our list and displays its details
                    }
                }
            }
        });

        // Load products when window opens
        loadListings();
    }

    // Retrieves marketplace listings from Flask
    private void loadListings() {

        final String searchText = searchField.getText().trim(); //gets what the client wrote and gets rif of any spaces pre or post

        searchButton.setEnabled(false); // while loading we disable serach so they cant just spam the buttons whil it loads
        refreshButton.setEnabled(false);

        statusLabel.setText("Loading listings..."); // set the thing we made before, to this, while waiting

        // while flask is sending over the infomration the site is still workable and not frozen by letting the java asking for flask be a background task with swing-worker
        new SwingWorker<List<Listing>, Void>() {

            @Override
            protected List<Listing> doInBackground() throws Exception { // the swing worker is the worker the doInBackground tells the worker what to do

                String url = API_URL; // making a stunt double so we dont alter API_URL directly

                // if search bar is empty
                if (!searchText.isEmpty()) {

                    url += "?q=" + URLEncoder.encode( // takes what was searched adds ?q= and then what you put in the bar. the encode thing makes it URLfriendly
                            searchText,
                            StandardCharsets.UTF_8 // what I am using to encode this
                    );
                }


                // the messenger
                HttpClient client = HttpClient.newBuilder() // we are creating a communactor variable that connectes flask and java with these parameters
                        .connectTimeout(Duration.ofSeconds(4)) // dont wait more than 4 secs
                        .build(); // build it

                
                //the message
                HttpRequest request = HttpRequest.newBuilder( // creating a message variable
                                URI.create(url) // converts the URL we had into a URI object something that java can use to request the info
                        )
                        .timeout(Duration.ofSeconds(10)) // time limit for how long this request can take
                        .GET() // what we are asking java to do. we want info from flask and java has to get it which is a function we have
                        .build(); //create the message

                // Javas response send GET request
                HttpResponse<String> response = client.send( //sending message to flask awaiting response
                        request, // what we built earlier the request we wanted.
                        HttpResponse.BodyHandlers.ofString() // takes the response and makes it into a string
                );

                
                if (response.statusCode() != 200) { // 200 is the code for success in http so if it is not a success

                    throw new IllegalStateException( // we throw an error saying the server did not respond right
                            "Server returned HTTP " +
                                    response.statusCode() // we put the error code that flask gave us
                    );
                }

                // Convert JSON into Java listing objects. JSON is the language python and java speak so we take it then using the parseListings function create listings from it
                return parseListings(response.body());
            }

            @Override
            protected void done() { // when the swing worker background task is done we update the listings and

                searchButton.setEnabled(true); // re-enable the buttons we froze
                refreshButton.setEnabled(true);

                try {

                    displayedListings = get(); // get the listing that we got from flask

                    // Clear previous products and shows only what was searched for
                    tableModel.setRowCount(0);

                    // Insert products into table
                    for (int i = 0; i < displayedListings.size(); i++) { // loop through all the listings
                     Listing item = displayedListings.get(i); // make item point at the current item we have

                        tableModel.addRow(new Object[]{ // add a row to the table with our new info

                                item.title, // the current items titel

                                String.format( // were making thus specifally candian based on locale a thing we imported
                                        Locale.CANADA,
                                        "$%.2f", // how many digits we allow after decimal
                                        item.priceCents / 100.0 // divide by 100 so we get the cents into dollars
                                ),

                                item.category, // current items category

                                item.condition.replace('_', ' '), // current items condition turned from flask x_x to x x

                                item.seller // current items seller
                        });
                    }

                    statusLabel.setText( // updates the status label at the bottom to say
                            displayedListings.size() + // amount of listings found and double click for details
                                    " listing(s) found. " + 
                                    "Double-click for details."
                    );

                } catch (Exception ex) { // an error occurs, handle it here instead of crashing the program


                    statusLabel.setText(
                            "Could not load listings. " + // update label with this
                                    "Is the Flask server running?"
                    );

                    JOptionPane.showMessageDialog( // create a popup window with the error message
                            main.this, // referes to our current marketplace window

                            "Unable to contact the backend.\n\n" +
                                    ex.getMessage() + // ex is the error infor, getMessage gets the message inside error and we are adding it to this text
                                    "\n\nStart Flask from the project's backend folder.",

                            "Connection problem",

                            JOptionPane.ERROR_MESSAGE // make the popup an error message with cool java semantics.
                    );
                }
            }

        }.execute(); // runs the background task the swing worker is gonna do
    }

    // Opens a box that has product information
    private void showListing(Listing item) { // we recive an item

        JTextArea details = new JTextArea( // items details in a text area, Area can have multiple lines field only one

                "Item: " + item.title + "\n" + // title

                "Price: " + String.format( // price using canadian money
                        Locale.CANADA,
                        "$%.2f", // rounding
                        item.priceCents / 100.0
                ) + "\n" +

                "Category: " + item.category + "\n" + // category 

                "Condition: " +
                        item.condition.replace('_', ' ') + "\n" + // switch from x_x to x x

                "Seller: " + item.seller + "\n\n" + // whos selling it

                "Description:\n" + item.description // item description
        );

        details.setEditable(false); // cannot edit one of the dunctions of JtextArea
        details.setLineWrap(true);  // move to next line if needed
        details.setWrapStyleWord(true); //keeps words together insetad of sending half a word to the next line if needed the whole word will be sent

        details.setBackground( // details is our box we are setting the background
                UIManager.getColor("Panel.background") // panel.background is the default that swing uses so that details isnt a different colour than the other part of the window
        );

        JOptionPane.showMessageDialog( // swing builder to make a popup
                this, // for our window
                details, // this specifc box
                "Listing details", // title
                JOptionPane.INFORMATION_MESSAGE // type of icon like the other one did error this does information
        );
    }

    // Converts JSON response into a list of products
    private static List<Listing> parseListings(String json) {

        JsonElement result = JsonParser.parseString(json); // we take the data from flask as a JSON and using the parser convert it into GSON something java can work with
        if (!result.isJsonArray()) { // if wha we receive isnt a list of listing
            throw new IllegalArgumentException( // throw an exception
                    "Expected a JSON list from the server"
            );
        }

        List<Listing> listings = new ArrayList<>(); // create an empty list for the info were about to get

        // Identify each listing object in the JSON array
        for (int i = 0; i < result.getAsJsonArray().size(); i++) {
        JsonElement element = result.getAsJsonArray().get(i); // we loop through the array of elements we got then we get the element from get (i) which is the item we want and store it in element
            if (!element.isJsonObject()) {
                throw new IllegalArgumentException("Expected a JSON listing object"); // throws error if we dont get a JSON object like we should
            }

            JsonObject fields = element.getAsJsonObject(); // allows us to acsess the elemnts through JSON so we can extract the keys and values
            if (!hasValue(fields, "title") || !hasValue(fields, "price_cents")) {
                throw new IllegalArgumentException("Missing listing fields"); // if the key does not have a title or price_cents throw error
            }

                    // Create a Java product object using all the data we just got
            listings.add(new Listing(
                    fields.get("title").getAsString(),
                    fields.get("price_cents").getAsInt(),
                    getString(fields, "category_name"),
                    getString(fields, "condition"),
                    getString(fields, "seller_name"),
                    getString(fields, "description")
            ));
        }

        return listings;
    }

    private static boolean hasValue(JsonObject fields, String key) { // checking if the current object has value
        return fields.has(key) && !fields.get(key).isJsonNull(); // checking if the key value is not null
    }

    private static String getString(JsonObject fields, String key) { // check if we have a value in the sting if so get it if not return empty string
        return hasValue(fields, key) ? fields.get(key).getAsString() : "";
    }

    // Represents one marketplace listing and setting all the things you need to define a listing
    private static class Listing {

        //variables needed to make a listing
        final String title;
        final String category;
        final String condition;
        final String seller;
        final String description;

        final int priceCents;

        Listing( // listing constructor
                String title,
                int priceCents,
                String category,
                String condition,
                String seller,
                String description
        ) {

            this.title = title; // this referes ti the the current object being made instead of the consturctot
            this.priceCents = priceCents;
            this.category = category;
            this.condition = condition;
            this.seller = seller;
            this.description = description;
        }
    }

    // Entry point of the application where the application starts running
    public static void main(String[] args) {

        SwingUtilities.invokeLater( // makes it so that swing runs everything correctly
                () -> new LoginScreen().setVisible(true) // displays everything we just made into that windoe w
        );
    }
}
