import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;

public class ConnectionTest {

    public static void main(String[] args) {
        String sql = "SELECT * FROM accounts";

        try (Connection connection =
                 DatabaseConnection.getConnection();
             Statement statement = connection.createStatement();
             ResultSet result = statement.executeQuery(sql)) {

            System.out.println("Connected to MySQL successfully!");
            System.out.println("Accounts table is accessible.");

            while (result.next()) {
                System.out.println(
                    "Username: " + result.getString("username")
                );
            }

        } catch (Exception e) {
            System.out.println("Test failed:");
            e.printStackTrace();
        }
    }
}
