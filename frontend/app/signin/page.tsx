import { Suspense } from "react";

import { AuthForm } from "@/components/AuthForm";

export default function SignInPage() {
  // Suspense is needed because the form reads ?next= from the URL.
  return (
    <Suspense>
      <AuthForm mode="signin" />
    </Suspense>
  );
}
