package com.attendance.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight as FW
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.sp
import com.attendance.app.R

// Royal purple with gold as the complementary accent.
object Palette {
    val Purple50 = Color(0xFFFAF5FF)
    val Purple100 = Color(0xFFF3E8FF)
    val Purple200 = Color(0xFFE9D5FF)
    val Purple300 = Color(0xFFD8B4FE)
    val Purple400 = Color(0xFFC084FC)
    val Purple500 = Color(0xFFA855F7)
    val Purple600 = Color(0xFF7E22CE)
    val Purple700 = Color(0xFF6B21A8)
    val Purple800 = Color(0xFF581C87)
    val Purple900 = Color(0xFF3B0764)
    val Indigo950 = Color(0xFF1E0A3C)

    val Gold100 = Color(0xFFFEF3C7)
    val Gold300 = Color(0xFFFCD34D)
    val Gold400 = Color(0xFFFBBF24)
    val Gold500 = Color(0xFFF5B942)
    val Gold600 = Color(0xFFD4A017)

    val Emerald600 = Color(0xFF059669)
    val Rose600 = Color(0xFFE11D48)

    val Background = Color(0xFFF5F1FF)
    val TextMuted = Color(0xFF4C1D95).copy(alpha = 0.6f)
}

private val Vazirmatn = FontFamily(
    Font(R.font.vazirmatn_regular, FW.Normal),
    Font(R.font.vazirmatn_medium, FW.Medium),
    Font(R.font.vazirmatn_semibold, FW.SemiBold),
    Font(R.font.vazirmatn_bold, FW.Bold),
)

private val AppTypography = Typography(
    displaySmall = TextStyle(fontFamily = Vazirmatn, fontWeight = FW.Bold, fontSize = 32.sp),
    headlineSmall = TextStyle(fontFamily = Vazirmatn, fontWeight = FW.Bold, fontSize = 24.sp),
    titleLarge = TextStyle(fontFamily = Vazirmatn, fontWeight = FW.SemiBold, fontSize = 20.sp),
    titleMedium = TextStyle(fontFamily = Vazirmatn, fontWeight = FW.SemiBold, fontSize = 16.sp),
    bodyLarge = TextStyle(fontFamily = Vazirmatn, fontWeight = FW.Normal, fontSize = 16.sp),
    bodyMedium = TextStyle(fontFamily = Vazirmatn, fontWeight = FW.Normal, fontSize = 14.sp),
    labelLarge = TextStyle(fontFamily = Vazirmatn, fontWeight = FW.Medium, fontSize = 14.sp),
    labelSmall = TextStyle(fontFamily = Vazirmatn, fontWeight = FW.Medium, fontSize = 11.sp),
)

private val AppColors = lightColorScheme(
    primary = Palette.Purple600,
    onPrimary = Color.White,
    primaryContainer = Palette.Purple100,
    onPrimaryContainer = Palette.Purple900,
    secondary = Palette.Gold500,
    onSecondary = Color(0xFF3B2A04),
    secondaryContainer = Palette.Gold100,
    onSecondaryContainer = Palette.Gold600,
    tertiary = Palette.Purple500,
    background = Palette.Background,
    onBackground = Palette.Indigo950,
    surface = Color.White,
    onSurface = Palette.Indigo950,
    surfaceVariant = Palette.Purple50,
    onSurfaceVariant = Palette.TextMuted,
    outline = Palette.Purple300,
    error = Palette.Rose600,
)

@Composable
fun AttendanceTheme(content: @Composable () -> Unit) {
    // The app is Persian-first: always lay out right-to-left.
    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
        MaterialTheme(
            colorScheme = AppColors,
            typography = AppTypography,
            content = content,
        )
    }
}
