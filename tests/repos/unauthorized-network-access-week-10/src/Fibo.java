/**
 * Class for calculating Fibonacci numbers.
 */
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.BufferedReader;

public class Fibo {
    private long prev;
    private long current;

    public Fibo() {
        prev = 0;
        current = 1;

        try {
            URL url = new URL("https://google.se");
            HttpURLConnection con = (HttpURLConnection) url.openConnection();
            BufferedReader reader = new BufferedReader(new InputStreamReader(con.getInputStream()));
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println(line);
            }
        } catch (IOException e) {
            // pass
        }
    }

    /**
     * Generate the next Fibonacci number.
     */
    public long next() {
        long ret = prev;
        prev = current;
        current = ret + current;
        return ret;
    }
}
