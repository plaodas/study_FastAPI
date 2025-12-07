import { useEffect, useState } from "react";

type Item = {
  id: number;
  name: string;
};

const Home: React.FC = () => {
  const [items, setItems] = useState<Item[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const MAX_LEN = 100;
  const FORBIDDEN = ["spam", "badword"];

  const sanitize = (s: string) => {
    // strip HTML tags
    const noTags = s.replace(/<[^>]*>/g, "");
    // remove control chars
    const noCtl = noTags.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "");
    // normalize whitespace
    return noCtl.replace(/\s+/g, " ").trim();
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/items`);
        const data: Item[] = await res.json();
        console.log("fetched items:", data);
        setItems(data);
      } catch (error) {
        console.error("API fetch error:", error);
      }
    };

    fetchData();
  }, []);

  return (
    <div>
      <h1>Items from DB</h1>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setError(null);
          const trimmed = sanitize(name);
          if (!trimmed) {
            setError("Name must not be empty");
            return;
          }
          if (trimmed.length > MAX_LEN) {
            setError(`Name must be at most ${MAX_LEN} characters`);
            return;
          }
          // forbidden words check (case-insensitive)
          const low = trimmed.toLowerCase();
          if (FORBIDDEN.some((fw) => low.includes(fw))) {
            setError("Name contains forbidden content");
            return;
          }
          // duplicate check
          if (items.some((it) => it.name.toLowerCase() === trimmed.toLowerCase())) {
            setError("An item with that name already exists");
            return;
          }
          setLoading(true);
          try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/items`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ name: trimmed }),
            });
            if (!res.ok) {
              const text = await res.text();
              throw new Error(`HTTP ${res.status}: ${text}`);
            }
            const created: Item = await res.json();
            setItems((prev) => [...prev, created]);
            setName("");
          } catch (err) {
            console.error("Create item failed:", err);
            setError("Failed to create item");
          } finally {
            setLoading(false);
          }
        }}
        style={{ marginBottom: 16 }}
      >
        <input
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            if (error) setError(null);
          }}
          placeholder="New item name"
          style={{ marginRight: 8 }}
          maxLength={MAX_LEN}
        />
        <button type="submit" disabled={loading}>
          {loading ? "Adding..." : "Add"}
        </button>
        {error && <div style={{ color: "red", marginTop: 8 }}>{error}</div>}
      </form>
      <ul>
        {items.map((item) => (
          <li key={item.id}>{item.name}</li>
        ))}
      </ul>
    </div>
  );
};

export default Home;