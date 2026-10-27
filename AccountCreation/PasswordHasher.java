package p2;

import java.security.SecureRandom;
import java.security.spec.KeySpec;
import java.util.Base64;
import java.security.MessageDigest;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;

public class PasswordHasher {

    private static final int ITERATIONS = 210000;
    private static final int SALT_LENGTH = 16;
    private static final int HASH_LENGTH = 256;

    public static String hashPassword(String password) throws Exception {
        byte[] salt = new byte[SALT_LENGTH];
        new SecureRandom().nextBytes(salt);
        PBEKeySpec spec = new PBEKeySpec(
            password.toCharArray(),
            salt,
            ITERATIONS,
            HASH_LENGTH
        );

        byte[] hash;
        try {
            SecretKeyFactory factory =
                SecretKeyFactory.getInstance(
                    "PBKDF2WithHmacSHA256"
                );

            hash = factory.generateSecret(spec).getEncoded();
        } finally {
            spec.clearPassword();
        }

        return ITERATIONS + ":"
            + Base64.getEncoder().encodeToString(salt) + ":"
            + Base64.getEncoder().encodeToString(hash);
    }

public static boolean verifyPassword(String password, String storedValue)
        throws Exception {

    String[] parts = storedValue.split(":");

    if (parts.length != 3) {
        return false;
    }

    int iterations = Integer.parseInt(parts[0]);
    byte[] salt = Base64.getDecoder().decode(parts[1]);
    byte[] expectedHash = Base64.getDecoder().decode(parts[2]);

    PBEKeySpec spec = new PBEKeySpec(
        password.toCharArray(),
        salt,
        iterations,
        expectedHash.length * 8
    );
    byte[] actualHash;
    try {
        SecretKeyFactory factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256");
        actualHash = factory.generateSecret(spec).getEncoded();
    } finally {
        spec.clearPassword();
    }
    return MessageDigest.isEqual(expectedHash, actualHash);
}

}
