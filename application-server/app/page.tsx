type OfferCard = {
  title: string;
  summary: string;
  price_hint: string;
  source_url: string;
  matched_keywords: string[];
};

type FuelStationPrice = {
  station_name: string;
  location: string;
  e5_price: number;
  e10_price: number;
  diesel_price: number;
  updated_at: string;
};

type ApplicationData = {
  supermarket_offers: OfferCard[];
  fuel_prices: FuelStationPrice[];
  generated_at: string;
};

async function getData(): Promise<ApplicationData> {
  const baseUrl = process.env.DATA_ANALYTICS_URL || process.env.NEXT_PUBLIC_DATA_ANALYTICS_URL || "http://localhost:8000";
  const response = await fetch(`${baseUrl}/api/application-data`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to load application data.");
  }
  return response.json();
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
  }).format(value);
}

export default async function HomePage() {
  const data = await getData();
  const cheapestE5 = [...data.fuel_prices].sort((a, b) => a.e5_price - b.e5_price)[0];

  return (
    <main className="page-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Application Server</p>
          <h1>Market intelligence for supermarket offers and fuel prices</h1>
          <p className="intro">
            This UI consumes curated data from the Data-Analytics Server and
            presents it in a clean comparison experience optimized for desktop and mobile.
          </p>
        </div>
        <div className="hero-stat">
          <span>Cheapest E5 right now</span>
          <strong>{cheapestE5 ? formatCurrency(cheapestE5.e5_price) : "n/a"}</strong>
          <small>{cheapestE5 ? `${cheapestE5.station_name}, ${cheapestE5.location}` : "No fuel data available"}</small>
        </div>
      </section>

      <section className="content-grid">
        <div className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Supermarkets</p>
              <h2>Current offers</h2>
            </div>
            <span className="badge">{data.supermarket_offers.length} items</span>
          </div>

          <div className="offer-list">
            {data.supermarket_offers.length > 0 ? (
              data.supermarket_offers.map((offer, index) => (
                <article className="offer-card" key={`${offer.source_url}-${index}`}>
                  <div className="offer-meta">
                    <span className="price-pill">{offer.price_hint}</span>
                    <span className="keyword-stack">{offer.matched_keywords.join(", ") || "general"}</span>
                  </div>
                  <h3>{offer.title}</h3>
                  <p>{offer.summary}</p>
                  <a href={offer.source_url} target="_blank" rel="noreferrer">
                    Open source
                  </a>
                </article>
              ))
            ) : (
              <div className="empty-state">
                No supermarket offers are stored yet. Submit a scrape job through the Data-Analytics Server.
              </div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Fuel</p>
              <h2>Price comparison</h2>
            </div>
            <span className="badge">Updated {new Date(data.generated_at).toLocaleTimeString("de-DE")}</span>
          </div>

          <div className="fuel-table-wrapper">
            <table className="fuel-table">
              <thead>
                <tr>
                  <th>Station</th>
                  <th>E5</th>
                  <th>E10</th>
                  <th>Diesel</th>
                </tr>
              </thead>
              <tbody>
                {data.fuel_prices.map((station) => (
                  <tr key={station.station_name}>
                    <td>
                      <strong>{station.station_name}</strong>
                      <span>{station.location}</span>
                    </td>
                    <td>{formatCurrency(station.e5_price)}</td>
                    <td>{formatCurrency(station.e10_price)}</td>
                    <td>{formatCurrency(station.diesel_price)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </main>
  );
}

