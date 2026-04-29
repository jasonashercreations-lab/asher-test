import { useEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import { Section, Button } from '@/components/ui/primitives';
import type { AssetList } from '@/types/project';
import { Upload, Trash2 } from 'lucide-react';

const KINDS = [
  { id: 'sprites' as const, label: 'Sprites', accept: 'image/png,image/jpeg,image/gif,image/webp', img: true },
  { id: 'logos'   as const, label: 'Logos',   accept: 'image/png,image/jpeg,image/gif,image/webp,image/svg+xml', img: true },
  { id: 'banners' as const, label: 'Banners', accept: 'image/png,image/jpeg,image/gif,image/webp', img: true },
  { id: 'fonts'   as const, label: 'Fonts',   accept: '.ttf,.otf,.bdf', img: false },
];

export function AssetsPanel() {
  const [assets, setAssets] = useState<AssetList | null>(null);

  const refresh = () => api.listAssets().then(setAssets).catch(() => setAssets({ sprites: [], logos: [], banners: [], fonts: [] }));
  useEffect(() => { refresh(); }, []);

  if (!assets) return <div className="px-3 py-4 text-xs text-muted">Loading…</div>;

  return (
    <div>
      <div className="px-3 py-2 border-b border-border bg-panel-2">
        <p className="text-[10px] text-muted">
          Upload custom team sprites, fonts, or banner art. Files are stored in the
          local assets directory and are immediately available to themes/teams.
        </p>
      </div>
      {KINDS.map((kind) => (
        <KindSection
          key={kind.id}
          kind={kind.id}
          label={kind.label}
          accept={kind.accept}
          isImage={kind.img}
          files={assets[kind.id]}
          onChange={refresh}
        />
      ))}
    </div>
  );
}

function KindSection({
  kind, label, accept, isImage, files, onChange,
}: {
  kind: 'sprites'|'fonts'|'logos'|'banners';
  label: string;
  accept: string;
  isImage: boolean;
  files: string[];
  onChange: () => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const upload = async (f: File) => {
    setUploading(true); setErr(null);
    try {
      await api.uploadAsset(kind, f);
      onChange();
    } catch (e: any) {
      setErr(String(e?.message || e));
    } finally { setUploading(false); }
  };

  const del = async (name: string) => {
    if (!confirm(`Delete ${name}?`)) return;
    await api.deleteAsset(kind, name);
    onChange();
  };

  return (
    <Section
      title={`${label} (${files.length})`}
      action={
        <>
          <input
            ref={fileRef}
            type="file"
            accept={accept}
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void upload(f);
              e.target.value = '';
            }}
          />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="text-xs flex items-center gap-1 text-accent hover:underline disabled:opacity-50"
            title={`Upload ${label.toLowerCase()}`}
          >
            <Upload className="w-3 h-3" /> {uploading ? 'Uploading…' : 'Upload'}
          </button>
        </>
      }
    >
      {err && <p className="text-[10px] text-red-400 mb-2">{err}</p>}
      {files.length === 0 ? (
        <p className="text-[10px] text-muted">No {label.toLowerCase()} uploaded.</p>
      ) : isImage ? (
        <div className="grid grid-cols-3 gap-1.5">
          {files.map((name) => (
            <div key={name} className="relative group bg-panel-2 rounded p-1">
              <img
                src={api.assetUrl(kind, name)}
                alt={name}
                className="w-full h-16 object-contain"
              />
              <div className="text-[9px] text-muted truncate mt-1" title={name}>{name}</div>
              <button
                onClick={() => del(name)}
                className="absolute top-0.5 right-0.5 p-0.5 bg-bg/80 rounded text-muted hover:text-red-400 opacity-0 group-hover:opacity-100"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-1">
          {files.map((name) => (
            <div key={name} className="flex items-center text-xs bg-panel-2 px-2 py-1 rounded">
              <span className="flex-1 truncate font-mono" title={name}>{name}</span>
              <button onClick={() => del(name)} className="ml-1 p-0.5 text-muted hover:text-red-400">
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}
