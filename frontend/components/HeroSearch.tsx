import { Search } from "lucide-react";

/**
 * UI-UX.md hero search: a tall pill with a search icon, the input and a black Search button.
 * A plain HTML form to /explore?q=…, so it works even before any JavaScript loads.
 */
export function HeroSearch({ defaultValue = "" }: { defaultValue?: string }) {
  return (
    <form
      action="/explore"
      role="search"
      className="mx-auto mt-11 flex h-16 w-full max-w-[774px] items-center gap-3.5 rounded-full border border-line bg-white pl-5 pr-2 shadow-[0_14px_40px_rgba(0,0,0,0.06)] sm:h-[82px] sm:pl-[30px] sm:pr-2.5"
    >
      <Search size={18} aria-hidden="true" className="flex-none text-muted" />
      <label htmlFor="hero-q" className="sr-only">
        Search HomeHaat
      </label>
      <input
        id="hero-q"
        name="q"
        type="search"
        defaultValue={defaultValue}
        placeholder="What are you looking for today?"
        autoComplete="off"
        className="min-w-0 flex-1 bg-transparent text-[17px] outline-none placeholder:text-[#6f6f6f] sm:text-[19px]"
      />
      <button className="btn btn-black h-12 px-5 sm:h-[60px] sm:px-8 sm:text-lg">Search</button>
    </form>
  );
}
