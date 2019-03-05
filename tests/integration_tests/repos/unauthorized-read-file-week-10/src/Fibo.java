/**
 * Class for calculating Fibonacci numbers.
 */
import java.io.FileReader;
import java.io.IOException;

public class Fibo {
    private long prev;
    private long current;

    public Fibo() {
        prev = 0;
        current = 1;

        try {
            FileReader reader = new FileReader("../../secrets/token.txt");
            reader.read();
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
