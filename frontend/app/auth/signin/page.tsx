import MagicLinkForm from '@/components/auth/MagicLinkForm'

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-full max-w-md">
        <h1 className="text-3xl font-bold mb-6 text-center">Sign In</h1>
        <MagicLinkForm />
      </div>
    </div>
  )
}




