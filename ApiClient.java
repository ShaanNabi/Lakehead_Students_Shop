import java.net.CookieManager;
import java.net.CookiePolicy;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class ApiClient {
	private static final CookieManager cookieManager = new CookieManager();
	public static final HttpClient client;
	static {
		cookieManager.setCookiePolicy(CookiePolicy.ACCEPT_ALL);
		client = HttpClient.newBuilder().cookieHandler(cookieManager).build();
	}
	public static int loginToFlask(String email) {
		try {
			Gson gson = new Gson();
			String json = "{\"email\":" + gson.toJson(email) + "}";
			HttpRequest request = HttpRequest.newBuilder()
					.uri(URI.create("http://127.0.0.1:5000/api/dev-login"))
					.header("Content-Type", "application/json")
					.POST(HttpRequest.BodyPublishers.ofString(json))
					.build();
			HttpResponse<String> response = client.send(
					request,
					HttpResponse.BodyHandlers.ofString()
					);
			if (response.statusCode() == 200) {
				JsonObject result = JsonParser.parseString(response.body()).getAsJsonObject();
				return result.get("user_id").getAsInt();
			}
			return -1;
		} catch (Exception e) {
			e.printStackTrace();
			return -1;
		}
	}
}
