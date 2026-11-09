package p2;
import java.net.CookieManager;
import java.net.CookiePolicy;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import com.google.gson.Gson;

public class ApiClient {
	private static final CookieManager cookieManager = new CookieManager();
	public static final HttpClient client;
	static {
		cookieManager.setCookiePolicy(CookiePolicy.ACCEPT_ALL);
		client = HttpClient.newBuilder().cookieHandler(cookieManager).build();
	}
	public static boolean loginToFlask(String email) {
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
			return response.statusCode() == 200;
		} catch (Exception e) {
			e.printStackTrace();
			return false;
		}
	}
}
