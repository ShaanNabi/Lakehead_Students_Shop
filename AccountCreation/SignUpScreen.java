import javax.swing.*;
import javax.swing.BorderFactory;
import javax.swing.JFrame;
import javax.swing.JButton;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JTextField;
import javax.swing.JPasswordField;
import javax.swing.SwingConstants;
import java.awt.*;
import java.awt.BorderLayout;
import java.awt.FlowLayout;
import java.awt.Font;
import java.awt.GridLayout;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;


public class SignUpScreen extends JFrame{
	
	private JTextField usernameField;
	private JPasswordField passwordField;
	private JPasswordField confirmPasswordField;
	private JTextField emailField;
	private JLabel messageLabel;
	private JButton loginButton;

	public SignUpScreen() {

		setTitle("Sign Up");
		setSize(400, 350);
		setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
		setLocationRelativeTo(null);
		//create the panel for the application
		JPanel panel = new JPanel(new BorderLayout(10, 10));
		panel.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15));
		//place the sign up text at the top
		JLabel titleLabel = new JLabel("Create Account", SwingConstants.CENTER);
		titleLabel.setFont(new Font("Arial", Font.BOLD, 22));
		panel.add(titleLabel, BorderLayout.NORTH);
		//create a panel for the fields
		JPanel formPanel = new JPanel(new GridLayout(4, 2, 10, 10));
		//username field
		JLabel usernameLabel = new JLabel("Username:");
		usernameField = new JTextField();
		formPanel.add(usernameLabel);
		formPanel.add(usernameField);
		//email field
		JLabel emailLabel = new JLabel("Email:");
		emailField = new JTextField();
		formPanel.add(emailLabel);
		formPanel.add(emailField);
		//password field
		JLabel passwordLabel = new JLabel("Password:");
		passwordField = new JPasswordField();
		formPanel.add(passwordLabel);
		formPanel.add(passwordField);
		//confirm password
		JLabel confirmPasswordLabel = new JLabel("Confirm Password:");
		confirmPasswordField = new JPasswordField();
		formPanel.add(confirmPasswordLabel);
		formPanel.add(confirmPasswordField);
		//add the panel
		panel.add(formPanel, BorderLayout.CENTER);
		//create a panel for the message and buttons
		JPanel bottomPanel = new JPanel(new BorderLayout(5, 5));
		//add the message
		messageLabel = new JLabel(" ", SwingConstants.CENTER);
		bottomPanel.add(messageLabel, BorderLayout.NORTH);
		//add the buttons
		JButton signUpButton = new JButton("Sign Up");
		signUpButton.addActionListener(e -> checkInput());
		bottomPanel.add(signUpButton, BorderLayout.CENTER);
		//create a seperate panel for the button to send the user to the login screen if an account is already made
		JPanel loginPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT));
		loginButton = new JButton("Already have an account? Login");
		//check if the user clicks the button, and send them to the login screen
		loginButton.addActionListener(e -> {
			new LoginScreen();
			dispose();
			}
		);
		//add login button
		loginPanel.add(loginButton);
		bottomPanel.add(loginPanel, BorderLayout.SOUTH);
		//add panel
		panel.add(bottomPanel, BorderLayout.SOUTH);
		add(panel);
		setVisible(true);
		}
	private void checkInput() {
   
		String username = usernameField.getText().trim();
		String email = emailField.getText().trim();
		String password = new String(passwordField.getPassword());
		String confirmPassword = new String(confirmPasswordField.getPassword());

		if (username.isEmpty() || email.isEmpty() || password.isEmpty() || confirmPassword.isEmpty()) {
			messageLabel.setText("Please fill in all fields.");
			messageLabel.setForeground(Color.RED);
		return;
		}
		if (!email.matches("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")) {
			messageLabel.setText("Please enter a valid email address.");
			messageLabel.setForeground(Color.RED);
        return;
		}
		if (!password.equals(confirmPassword)) {
			messageLabel.setText("Passwords do not match.");
			messageLabel.setForeground(Color.RED);
        return;
		}

    String sql =
        "INSERT INTO accounts (username, email, password_hash) VALUES (?, ?, ?)";

    try {
        //hash the password so if someone has access to the database they will be unable to see the users password
        String passwordHash = PasswordHasher.hashPassword(password);

        //connect to the SQL server to save the account information
        try (Connection connection = DatabaseConnection.getConnection();
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, username);
            statement.setString(2, email);
            statement.setString(3, passwordHash);
            statement.executeUpdate();
        }
        messageLabel.setText("Account created successfully!");
        messageLabel.setForeground(new Color(0, 130, 0));

        //clear the fields after a user signs up
        usernameField.setText("");
        emailField.setText("");
        passwordField.setText("");
        confirmPasswordField.setText("");

    } catch (SQLException e) {
    	//prevent duplicate emails or usernames
        if ("23000".equals(e.getSQLState())) {
            messageLabel.setText("That username or email is already taken.");
            messageLabel.setForeground(Color.RED);
            //check for other errors
        } else {
            messageLabel.setText("Database error. Please try again.");
            messageLabel.setForeground(Color.RED);
            e.printStackTrace();
        }

        //check for any password errors
    } catch (Exception e) {
        messageLabel.setText("Could not process the password.");
        messageLabel.setForeground(Color.RED);
        e.printStackTrace();
    }
}
    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            SignUpScreen screen = new SignUpScreen();
            screen.setVisible(true);
            });
    	}
	}
