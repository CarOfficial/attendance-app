import { useEffect, useRef, useState, type FormEvent } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api, ApiError } from "../api";
import { Alert, Badge, Button, Card, ConfirmDialog, Empty, Field, Input, Table } from "../components/ui";
import type { Branch } from "../types";

// Tehran as the default map center.
const DEFAULT_CENTER: [number, number] = [35.6892, 51.389];

interface FormState {
  id: number | null;
  name: string;
  address: string;
  latitude: string;
  longitude: string;
  radius_m: string;
  is_active: boolean;
}

const emptyForm: FormState = {
  id: null,
  name: "",
  address: "",
  latitude: String(DEFAULT_CENTER[0]),
  longitude: String(DEFAULT_CENTER[1]),
  radius_m: "100",
  is_active: true,
};

export function BranchesPage() {
  const [branches, setBranches] = useState<Branch[] | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<Branch | null>(null);
  const [force, setForce] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const attemptDelete = async () => {
    if (!deleting) return;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await api(`/admin/branches/${deleting.id}${force ? "?force=true" : ""}`, { method: "DELETE" });
      setNotice(`دفتر «${deleting.name}» حذف شد.`);
      setDeleting(null);
      setForce(false);
      void load();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setForce(true);
        setDeleteError("این دفتر سابقه حضور دارد. با تایید دوباره، دفتر همراه با سوابق حضور آن حذف می‌شود.");
      } else {
        setDeleteError(e instanceof ApiError ? e.message : "خطا در حذف دفتر");
      }
    } finally {
      setDeleteBusy(false);
    }
  };

  const load = () =>
    api<Branch[]>("/admin/branches")
      .then(setBranches)
      .catch((e) => setError(e instanceof ApiError ? e.message : "خطا در دریافت دفاتر"));

  useEffect(() => {
    void load();
  }, []);

  const edit = (b: Branch) =>
    setForm({
      id: b.id,
      name: b.name,
      address: b.address ?? "",
      latitude: String(b.latitude),
      longitude: String(b.longitude),
      radius_m: String(b.radius_m),
      is_active: b.is_active,
    });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-royal-gradient">دفاتر و موقعیت</h1>
          <p className="mt-1 text-sm text-slate-500">
            موقعیت هر دفتر را روی نقشه مشخص کنید. کارمندان فقط داخل شعاع تعیین‌شده می‌توانند ثبت حضور کنند.
          </p>
        </div>
        <Button onClick={() => setForm({ ...emptyForm })}>+ دفتر جدید</Button>
      </div>

      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      {form && (
        <BranchForm
          initial={form}
          onCancel={() => setForm(null)}
          onSaved={(msg) => {
            setForm(null);
            setNotice(msg);
            void load();
          }}
        />
      )}

      <Card>
        {branches === null ? (
          <Empty>در حال بارگذاری…</Empty>
        ) : branches.length === 0 ? (
          <Empty>هنوز دفتری تعریف نشده است.</Empty>
        ) : (
          <Table head={["نام دفتر", "آدرس", "مختصات", "شعاع مجاز", "وضعیت", ""]}>
            {branches.map((b) => (
              <tr key={b.id}>
                <td className="px-4 py-3 font-medium text-slate-800">{b.name}</td>
                <td className="px-4 py-3 text-slate-600">{b.address || "—"}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-500" dir="ltr">
                  {b.latitude.toFixed(5)}, {b.longitude.toFixed(5)}
                </td>
                <td className="px-4 py-3 tabular-nums">{Math.round(b.radius_m)} متر</td>
                <td className="px-4 py-3">
                  {b.is_active ? <Badge tone="green">فعال</Badge> : <Badge tone="slate">غیرفعال</Badge>}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-left">
                  <button onClick={() => edit(b)} className="text-sm text-indigo-600 hover:underline">ویرایش</button>
                  <button
                    onClick={() => {
                      setForce(false);
                      setDeleteError(null);
                      setDeleting(b);
                    }}
                    className="mr-3 text-sm text-rose-600 hover:underline"
                  >
                    حذف
                  </button>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>

      {deleting && (
        <ConfirmDialog
          title={`حذف دفتر «${deleting.name}»`}
          description={
            force
              ? "این دفتر سابقه حضور دارد؛ با تایید، سوابق حضور مرتبط با آن هم حذف می‌شود."
              : "دفتر از فهرست دفاتر حذف می‌شود و کارمندان دیگر نمی‌توانند در آن ثبت حضور کنند."
          }
          confirmLabel={force ? "حذف با سوابق" : "حذف دفتر"}
          busy={deleteBusy}
          error={deleteError}
          onCancel={() => {
            setDeleting(null);
            setForce(false);
            setDeleteError(null);
          }}
          onConfirm={attemptDelete}
        />
      )}
    </div>
  );
}

function BranchForm({ initial, onCancel, onSaved }: {
  initial: FormState;
  onCancel: () => void;
  onSaved: (msg: string) => void;
}) {
  const [f, setF] = useState<FormState>(initial);
  const [localError, setLocalError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const lat = Number(f.latitude);
  const lng = Number(f.longitude);
  const radius = Number(f.radius_m);
  const validPoint = Number.isFinite(lat) && Number.isFinite(lng);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setF((prev) => ({ ...prev, [key]: value }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    if (!validPoint) return setLocalError("مختصات معتبر نیست. روی نقشه کلیک کنید.");
    if (!(radius >= 20 && radius <= 1000)) return setLocalError("شعاع باید بین ۲۰ تا ۱۰۰۰ متر باشد");

    const body = {
      name: f.name.trim(),
      address: f.address.trim() || null,
      latitude: lat,
      longitude: lng,
      radius_m: radius,
      is_active: f.is_active,
    };
    setBusy(true);
    try {
      if (f.id === null) {
        await api("/admin/branches", { method: "POST", body });
        onSaved("دفتر جدید ثبت شد.");
      } else {
        await api(`/admin/branches/${f.id}`, { method: "PATCH", body });
        onSaved("تغییرات دفتر ذخیره شد.");
      }
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "خطا در ذخیره";
      setLocalError(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title={f.id === null ? "دفتر جدید" : `ویرایش ${initial.name}`}>
      <form onSubmit={submit} className="grid gap-6 lg:grid-cols-5">
        <div className="space-y-4 lg:col-span-2">
          {localError && <Alert>{localError}</Alert>}
          <Field label="نام دفتر">
            <Input value={f.name} onChange={(e) => set("name", e.target.value)} required minLength={2} />
          </Field>
          <Field label="آدرس (اختیاری)">
            <Input value={f.address} onChange={(e) => set("address", e.target.value)} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="عرض جغرافیایی">
              <Input value={f.latitude} onChange={(e) => set("latitude", e.target.value)} dir="ltr" required />
            </Field>
            <Field label="طول جغرافیایی">
              <Input value={f.longitude} onChange={(e) => set("longitude", e.target.value)} dir="ltr" required />
            </Field>
          </div>
          <Field label="شعاع مجاز (متر)" hint="پیشنهاد: ۸۰ تا ۱۵۰ متر برای یک ساختمان">
            <Input type="number" min={20} max={1000} value={f.radius_m} onChange={(e) => set("radius_m", e.target.value)} dir="ltr" required />
          </Field>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={f.is_active} onChange={(e) => set("is_active", e.target.checked)} className="h-4 w-4 accent-purple-700" />
            دفتر فعال باشد
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={onCancel}>انصراف</Button>
            <Button type="submit" disabled={busy}>{busy ? "در حال ذخیره…" : "ذخیره"}</Button>
          </div>
        </div>
        <div className="lg:col-span-3">
          <MapPicker
            lat={validPoint ? lat : DEFAULT_CENTER[0]}
            lng={validPoint ? lng : DEFAULT_CENTER[1]}
            radius={Number.isFinite(radius) ? radius : 100}
            onPick={(la, ln) => {
              set("latitude", la.toFixed(6));
              set("longitude", ln.toFixed(6));
            }}
          />
          <p className="mt-2 text-xs text-slate-500">روی نقشه کلیک کنید تا موقعیت دفتر تنظیم شود. دایره نشان‌دهنده‌ی شعاع مجاز است.</p>
        </div>
      </form>
    </Card>
  );
}

function MapPicker({ lat, lng, radius, onPick }: {
  lat: number;
  lng: number;
  radius: number;
  onPick: (lat: number, lng: number) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.CircleMarker | null>(null);
  const circleRef = useRef<L.Circle | null>(null);
  const onPickRef = useRef(onPick);
  onPickRef.current = onPick;

  // Create the map once.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, { zoomControl: true }).setView([lat, lng], 16);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap",
    }).addTo(map);
    map.on("click", (e: L.LeafletMouseEvent) => onPickRef.current(e.latlng.lat, e.latlng.lng));
    mapRef.current = map;
    return () => {
      map.remove();
      // Layers belong to the removed map; drop refs so they are recreated on the next map.
      mapRef.current = null;
      markerRef.current = null;
      circleRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync marker and radius circle with form values.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (!markerRef.current) {
      markerRef.current = L.circleMarker([lat, lng], { radius: 7, color: "#4f46e5", fillColor: "#6366f1", fillOpacity: 1 }).addTo(map);
    } else {
      markerRef.current.setLatLng([lat, lng]);
    }
    if (!circleRef.current) {
      circleRef.current = L.circle([lat, lng], { radius, color: "#4f46e5", weight: 2, fillOpacity: 0.12 }).addTo(map);
    } else {
      circleRef.current.setLatLng([lat, lng]).setRadius(radius);
    }
    map.panTo([lat, lng], { animate: true });
  }, [lat, lng, radius]);

  return <div ref={containerRef} className="h-80 w-full overflow-hidden rounded-3xl border border-white/80 shadow-lg shadow-indigo-900/10 lg:h-[26rem]" />;
}
