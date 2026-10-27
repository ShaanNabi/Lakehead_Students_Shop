import java.awt.GridLayout;
import java.awt.BorderLayout;
import java.awt.FlowLayout;
import java.awt.Font;
import javax.swing.JButton;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JPasswordField;
import javax.swing.JTextField;
import javax.swing.BorderFactory;
import javax.swing.SwingConstants;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class LoginScreen extends JFrame {

    private JTextField usernameField;
    private JPasswordField passwordField;
    private JButton loginButton;
    private JLabel messageLabel;
    private JButton signUpButton;


public LoginScreen() {
    setTitle("Login");
    setSize(400, 300);
    setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
    setLocationRelativeTo(null);

    //create the panel to display everything
    JPanel panel = new JPanel(new BorderLayout(10, 10));
    panel.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15));
    //place the login text at the top of the screen
    JLabel titleLabel = new JLabel("Login", SwingConstants.CENTER);
    titleLabel.setFont(new Font("Arial", Font.BOLD, 22));
    panel.add(titleLabel, BorderLayout.NORTH);
    //create the username and password fields
    JPanel formPanel = new JPanel(new GridLayout(2, 2, 10, 10));
    JLabel usernameLabel = new JLabel("Username:");
    usernameField = new JTextField();
    formPanel.add(usernameLabel);
    formPanel.add(usernameField);
    JLabel passwordLabel = new JLabel("Password:");
    passwordField = new JPasswordField();
    formPanel.add(passwordLabel);
    formPanel.add(passwordField);
    panel.add(formPanel, BorderLayout.CENTER);
    //add the message informing the user if the login was successful or not
    JPanel bottomPanel = new JPanel(new BorderLayout(5, 5));
    messageLabel = new JLabel(" ", SwingConstants.CENTER);
    bottomPanel.add(messageLabel, BorderLayout.NORTH);
    //panel for the buttons
    JPanel buttonsPanel = new JPanel(new BorderLayout());
    //create the login and sign up buttons
    loginButton = new JButton("Login");
    loginButton.addActionListener(e -> checkInput());
    buttonsPanel.add(loginButton, BorderLayout.EAST);
    signUpButton = new JButton("Create an account");
    //check if the users clicks it and send them to the login screen
    signUpButton.addActionListener(e -> {
       new SignUpScreen();
       dispose();
   });
   buttonsPanel.add(signUpButton, BorderLayout.WEST);
   bottomPanel.add(buttonsPanel, BorderLayout.SOUTH);
   panel.add(bottomPanel, BorderLayout.SOUTH);
    add(panel);
    setVisible(true);
}

private void checkInput() {
    String username = usernameField.getText().trim();
    String password = new String(passwordField.getPassword());
    //check if the user has entered a username or password
    if (username.isEmpty() || password.isEmpty()) {
        messageLabel.setText("Please enter username and password.");
        return;
    }
    //connect to the SQL server to get the information for the accounts
    String sql = "SELECT password_hash FROM accounts WHERE username = ?";
    try (Connection connection = DatabaseConnection.getConnection();
         PreparedStatement statement = connection.prepareStatement(sql)) {
        statement.setString(1, username);
        try (ResultSet result = statement.executeQuery()) {
            if (result.next()) {
                String storedHash = result.getString("password_hash");
                if (PasswordHasher.verifyPassword(password, storedHash)) {
                    messageLabel.setText("Login successful!");
                    main marketplace = new main();
                    marketplace.setVisible(true);
                    dispose();
                } else {
                    messageLabel.setText("Invalid username or password.");
                    passwordField.setText("");
                }
            } else {
                messageLabel.setText("Invalid username or password.");
                passwordField.setText("");
            }
        }
    } catch (SQLException e) {
        messageLabel.setText("Database error. Please try again.");
        e.printStackTrace();
    } catch (Exception e) {
        messageLabel.setText("Could not verify password.");
        e.printStackTrace();
    }
}
    public static void main(String[] args) {
        new LoginScreen();
    }
}
